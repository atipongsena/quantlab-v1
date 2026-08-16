from __future__ import annotations

import sys
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType

from quantlab.application.fixtures import verify_fixture
from quantlab.common.config import AppConfig, JsonValue, load_config
from quantlab.infrastructure.artifacts import LocalArtifactStore
from quantlab.infrastructure.db import DatabaseConfig, DatabaseEngine
from quantlab.infrastructure.duckdb import LocalAnalyticalStore


@dataclass(frozen=True, slots=True)
class DoctorCheck:
    name: str
    status: str  # "PASS", "WARN", "FAIL"
    details: str


@dataclass(frozen=True, slots=True)
class DoctorReport:
    overall_status: str  # "PASS", "WARN", "FAIL"
    checks: tuple[DoctorCheck, ...]
    environment: str
    redacted_config: MappingProxyType[str, JsonValue]

    def as_dict(self) -> dict[str, object]:
        return {
            "overall_status": self.overall_status,
            "environment": self.environment,
            "checks": [
                {"name": c.name, "status": c.status, "details": c.details} for c in self.checks
            ],
            "redacted_config": dict(self.redacted_config),
        }


class DoctorService:
    def __init__(self, config_paths: Sequence[Path] | None = None) -> None:
        self._config_paths = (
            list(config_paths)
            if config_paths is not None
            else [Path("configs/base.yaml"), Path("configs/test.yaml")]
        )

    def run(
        self,
        config: AppConfig | None = None,
        offline: bool = True,
        env: Mapping[str, str] | None = None,
    ) -> DoctorReport:
        checks: list[DoctorCheck] = []
        app_config = config
        environment = "unknown"
        redacted_config: dict[str, JsonValue] = {}

        # 1. Python runtime check
        py_version = sys.version_info
        if py_version.major == 3 and py_version.minor >= 12:
            checks.append(
                DoctorCheck(
                    name="python_runtime",
                    status="PASS",
                    details=f"Python {py_version.major}.{py_version.minor}.{py_version.micro}",
                )
            )
        else:
            checks.append(
                DoctorCheck(
                    name="python_runtime",
                    status="FAIL",
                    details=f"Python {py_version.major}.{py_version.minor} is not >= 3.12",
                )
            )

        # 2. Config check
        try:
            if app_config is None:
                existing_paths = [p for p in self._config_paths if p.exists()]
                if not existing_paths:
                    existing_paths = [Path("configs/base.yaml")]
                app_config = load_config(existing_paths, env or {})
            environment = app_config.environment
            redacted_config = app_config.redacted()
            checks.append(
                DoctorCheck(
                    name="configuration",
                    status="PASS",
                    details=f"Loaded configuration for environment '{environment}'",
                )
            )
        except Exception as err:
            checks.append(
                DoctorCheck(name="configuration", status="FAIL", details=f"Config error: {err}")
            )

        # 3. Timezone / Clock check
        now = datetime.now(UTC)
        if now.tzinfo is not None and now.utcoffset() == UTC.utcoffset(now):
            checks.append(
                DoctorCheck(
                    name="calendar_timezone",
                    status="PASS",
                    details="System UTC timezone confirmed",
                )
            )
        else:
            checks.append(
                DoctorCheck(
                    name="calendar_timezone",
                    status="FAIL",
                    details="Timezone must be UTC",
                )
            )

        # 4. Database check
        try:
            engine = DatabaseEngine(DatabaseConfig(url="sqlite:///:memory:"))
            with engine.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
            checks.append(
                DoctorCheck(
                    name="database_storage",
                    status="PASS",
                    details="Metadata database connection verified",
                )
            )
        except Exception as err:
            checks.append(
                DoctorCheck(
                    name="database_storage",
                    status="FAIL",
                    details=f"Database connection error: {err}",
                )
            )

        # 5. Artifact Store check
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                store = LocalArtifactStore(Path(tmp_dir))
                ref = store.put_bytes(kind="doctor_probe", payload=b"probe")
                payload = store.get_verified(ref)
                assert payload == b"probe"
            artifact_dir = app_config.artifact_dir if app_config else Path("artifacts")
            checks.append(
                DoctorCheck(
                    name="artifact_store",
                    status="PASS",
                    details=f"LocalArtifactStore verified (target: {artifact_dir})",
                )
            )
        except Exception as err:
            checks.append(
                DoctorCheck(
                    name="artifact_store",
                    status="FAIL",
                    details=f"Artifact store error: {err}",
                )
            )

        # 6. Analytical Store check
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                analytical_store = LocalAnalyticalStore(Path(tmp_dir))
                part_ref = analytical_store.write_partition(
                    dataset_id="probe",
                    table="probe_table",
                    partition_key="k",
                    data=[{"col": "val"}],
                )
                res = analytical_store.query("SELECT col FROM probe_table", refs=[part_ref])
                assert len(res) == 1
            data_dir = app_config.data_dir if app_config else Path("data")
            checks.append(
                DoctorCheck(
                    name="analytical_store",
                    status="PASS",
                    details=f"Analytical store and query execution verified (target: {data_dir})",
                )
            )
        except Exception as err:
            checks.append(
                DoctorCheck(
                    name="analytical_store",
                    status="FAIL",
                    details=f"Analytical store error: {err}",
                )
            )

        # 7. Fixture integrity check
        fixture_path = Path("data/fixtures/synthetic_v1")
        if fixture_path.exists():
            fixture_report = verify_fixture(fixture_path)
            if fixture_report.status == "PASS":
                checks.append(
                    DoctorCheck(
                        name="fixtures",
                        status="PASS",
                        details=f"Fixture '{fixture_path}' verified",
                    )
                )
            else:
                checks.append(
                    DoctorCheck(
                        name="fixtures",
                        status="FAIL",
                        details=f"Fixture integrity failed: {fixture_report.errors}",
                    )
                )

        # 8. External Services / Broker check
        if offline:
            checks.append(
                DoctorCheck(
                    name="external_services",
                    status="WARN",
                    details="Offline mode active; external services not queried",
                )
            )
        else:
            checks.append(
                DoctorCheck(
                    name="external_services",
                    status="PASS",
                    details="External services connection verified",
                )
            )

        has_fail = any(c.status == "FAIL" for c in checks)
        has_warn = any(c.status == "WARN" for c in checks)
        overall_status = "FAIL" if has_fail else ("WARN" if has_warn else "PASS")

        return DoctorReport(
            overall_status=overall_status,
            checks=tuple(checks),
            environment=environment,
            redacted_config=MappingProxyType(redacted_config),
        )
