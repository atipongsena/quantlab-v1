from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID

from quantlab.common.errors import QuantLabError
from quantlab.common.hashing import canonical_hash
from quantlab.data.quality import QualityReport
from quantlab.domain.identity import InstrumentId
from quantlab.infrastructure.analytical_store import LocalAnalyticalStore
from quantlab.infrastructure.artifacts import LocalArtifactStore
from quantlab.infrastructure.partitions import PARTITION_SUFFIX, PartitionRef, read_partition


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


class DatasetNotFoundError(QuantLabError):
    """Raised when a published dataset cannot be located on disk."""


@dataclass(frozen=True, slots=True)
class DatasetMember:
    """One instrument as recorded in a published dataset roster."""

    instrument_id: InstrumentId
    symbol: str
    name: str
    instrument_type: str
    exchange: str
    sector: str
    active_from: date
    active_to: date | None
    status: str

    @property
    def is_etf(self) -> bool:
        return self.instrument_type.lower() == "etf"


class DatasetUniverseResolver:
    """Reads the instrument roster a dataset was published with.

    Services take a ``--dataset`` argument, so they must resolve their universe from
    that dataset rather than from every instrument that happens to sit in the shared
    identity table. Two datasets built into the same working directory would otherwise
    contaminate each other's cross-sections.
    """

    def __init__(self, analytical_store: LocalAnalyticalStore) -> None:
        self._store = analytical_store

    def _roster_path(self, dataset_id: str) -> tuple[str, str] | None:
        table_dir = self._store.base_dir / dataset_id / "instruments"
        if not table_dir.is_dir():
            return None
        candidates = sorted(table_dir.glob(f"*{PARTITION_SUFFIX}"))
        if not candidates:
            return None
        newest = candidates[-1]
        return newest.stem, str(newest)

    def members(self, dataset_id: str) -> tuple[DatasetMember, ...]:
        located = self._roster_path(dataset_id)
        if located is None:
            raise DatasetNotFoundError(
                f"Dataset '{dataset_id}' has no published instrument roster. "
                f"Run `quantlab dataset build` for it first."
            )
        partition_key, uri = located
        ref = PartitionRef(
            dataset_id=dataset_id,
            table_name="instruments",
            partition_key=partition_key,
            uri=uri,
            row_count=0,
            content_hash="",
        )

        members: list[DatasetMember] = []
        for row in read_partition(ref):
            active_to_raw = str(row.get("active_to") or "").strip()
            members.append(
                DatasetMember(
                    instrument_id=InstrumentId.from_uuid(UUID(str(row["instrument_id"]))),
                    symbol=str(row["symbol"]),
                    name=str(row.get("name", "")),
                    instrument_type=str(row.get("type", "equity")),
                    exchange=str(row.get("exchange", "")),
                    sector=str(row.get("sector") or "UNKNOWN"),
                    active_from=date.fromisoformat(str(row["active_from"])),
                    active_to=date.fromisoformat(active_to_raw) if active_to_raw else None,
                    status=str(row.get("status", "active")),
                )
            )
        return tuple(sorted(members, key=lambda m: m.symbol))

    def equities(self, dataset_id: str) -> tuple[DatasetMember, ...]:
        """Cross-sectional research universe.

        Spec 2.7 keeps ETFs out of equity factor rankings: an index fund ranked against
        its own constituents is not a comparable cross-section.
        """
        return tuple(m for m in self.members(dataset_id) if not m.is_etf)

    def etfs(self, dataset_id: str) -> tuple[DatasetMember, ...]:
        return tuple(m for m in self.members(dataset_id) if m.is_etf)

    def benchmark(self, dataset_id: str, symbol: str) -> DatasetMember | None:
        for member in self.members(dataset_id):
            if member.symbol.upper() == symbol.upper():
                return member
        return None


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
