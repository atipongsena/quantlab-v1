from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from quantlab.common.hashing import canonical_hash
from quantlab.data.quality import QualityReport
from quantlab.infrastructure.artifacts import LocalArtifactStore
from quantlab.infrastructure.duckdb import LocalAnalyticalStore


@dataclass(frozen=True, slots=True)
class DatasetManifest:
    dataset_id: str
    version: str
    manifest_hash: str
    tables: dict[str, str]  # table_name -> partition_hash
    row_counts: dict[str, int]
    created_at: datetime
    quality_report: QualityReport | None

    def as_dict(self) -> dict[str, object]:
        return {
            "dataset_id": self.dataset_id,
            "version": self.version,
            "manifest_hash": self.manifest_hash,
            "tables": self.tables,
            "row_counts": self.row_counts,
            "created_at": self.created_at.isoformat(),
            "quality_report": self.quality_report.as_dict() if self.quality_report else None,
        }


class DatasetPublisher:
    def __init__(
        self,
        artifact_store: LocalArtifactStore,
        analytical_store: LocalAnalyticalStore,
    ) -> None:
        self._artifact_store = artifact_store
        self._analytical_store = analytical_store

    def publish(
        self,
        dataset_id: str,
        version: str,
        tables_data: Mapping[str, Sequence[Mapping[str, object]]],
        quality_report: QualityReport | None = None,
    ) -> DatasetManifest:
        tables: dict[str, str] = {}
        row_counts: dict[str, int] = {}

        for table_name, rows in tables_data.items():
            partition_ref = self._analytical_store.write_partition(
                dataset_id=dataset_id,
                table=table_name,
                partition_key=version,
                data=rows,
            )
            tables[table_name] = partition_ref.content_hash
            row_counts[table_name] = len(rows)

        now = datetime.now(UTC)
        manifest_payload = {
            "dataset_id": dataset_id,
            "version": version,
            "tables": tables,
            "row_counts": row_counts,
            "quality_report": quality_report.as_dict() if quality_report else None,
        }
        manifest_hash = canonical_hash(manifest_payload)

        manifest = DatasetManifest(
            dataset_id=dataset_id,
            version=version,
            manifest_hash=manifest_hash,
            tables=tables,
            row_counts=row_counts,
            created_at=now,
            quality_report=quality_report,
        )

        return manifest
