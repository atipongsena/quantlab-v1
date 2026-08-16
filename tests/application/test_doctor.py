from __future__ import annotations

from pathlib import Path

from quantlab.application.doctor import DoctorService
from quantlab.common.config import load_config


def test_doctor_offline_success() -> None:
    service = DoctorService()
    report = service.run(offline=True)

    assert report.overall_status in ("PASS", "WARN")
    check_names = {c.name: c.status for c in report.checks}
    assert check_names["python_runtime"] == "PASS"
    assert check_names["configuration"] == "PASS"
    assert check_names["calendar_timezone"] == "PASS"
    assert check_names["database_storage"] == "PASS"
    assert check_names["artifact_store"] == "PASS"
    assert check_names["analytical_store"] == "PASS"
    assert check_names["external_services"] == "WARN"


def test_doctor_redacts_secrets(tmp_path: Path) -> None:
    cfg_path = tmp_path / "custom.yaml"
    cfg_path.write_text(
        """
environment: test
timezone: UTC
data_dir: data/fixtures
artifact_dir: artifacts/test
log_level: DEBUG
secrets:
  api_key: super_secret_token_12345
  database_password: top_secret_db_pass
""",
        encoding="utf-8",
    )

    config = load_config([cfg_path], {})
    service = DoctorService(config_paths=[cfg_path])
    report = service.run(config=config, offline=True)

    redacted = report.redacted_config
    secrets = redacted.get("secrets")
    assert isinstance(secrets, dict)
    assert secrets["api_key"] == "***REDACTED***"
    assert secrets["database_password"] == "***REDACTED***"
