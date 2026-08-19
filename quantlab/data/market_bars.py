from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from quantlab.domain.identity import InstrumentId
from quantlab.domain.market import BarPriceSemantic, MarketBar
from quantlab.infrastructure.analytical_store import LocalAnalyticalStore
from quantlab.infrastructure.partitions import PARTITION_SUFFIX, PartitionRef, read_partition


class MarketBarStore:
    """Partitioned daily bar store.

    Partitions are keyed by ``{instrument}_{semantic}_{year}`` inside a per-dataset
    namespace. Both parts of that are load-bearing.

    The **semantic** keeps a build's RAW bars from being overwritten by any derived
    series written afterwards.

    The **namespace** keeps datasets apart. Instrument ids are derived from the symbol,
    so the same ticker resolves to the same id in every dataset. Sharing one namespace
    means building a second dataset that contains AAPL silently replaces the first
    dataset's AAPL prices for the overlapping years, and every downstream number is then
    computed on a blend of two datasets with nothing raising.
    """

    def __init__(
        self,
        analytical_store: LocalAnalyticalStore,
        namespace: str = "market_bars",
    ) -> None:
        self._store = analytical_store
        self._namespace = namespace

    @staticmethod
    def namespace_for(dataset_id: str) -> str:
        """Storage namespace for a dataset's bars."""
        return f"market_bars/{dataset_id}"

    @property
    def namespace(self) -> str:
        return self._namespace

    @staticmethod
    def _partition_key(instrument_id: InstrumentId, semantic: BarPriceSemantic, year: int) -> str:
        return f"{instrument_id.value}_{semantic.value}_{year}"

    def write_daily_bars(self, bars: Sequence[MarketBar]) -> None:
        if not bars:
            return

        # Group bars by instrument, price semantic, and year for partitioning
        by_partition: dict[str, list[dict[str, object]]] = {}
        for bar in bars:
            key = self._partition_key(bar.instrument_id, bar.semantic, bar.session.year)
            row: dict[str, object] = {
                "instrument_id": str(bar.instrument_id.value),
                "session": bar.session.isoformat(),
                "observed_at": bar.observed_at.isoformat(),
                "open": str(bar.open),
                "high": str(bar.high),
                "low": str(bar.low),
                "close": str(bar.close),
                "volume": str(bar.volume),
                "semantic": bar.semantic.value,
                "source": bar.source,
            }
            by_partition.setdefault(key, []).append(row)

        for partition_key, rows in by_partition.items():
            self._store.write_partition(
                dataset_id=self._namespace,
                table="daily",
                partition_key=partition_key,
                data=rows,
            )

    def list_sessions(self, instrument_id: InstrumentId, semantic: BarPriceSemantic) -> list[date]:
        """Return every session held for an instrument without materializing full bars."""
        prefix = f"{instrument_id.value}_{semantic.value}_"
        partition_dir = self._store.base_dir / self._namespace / "daily"
        if not partition_dir.is_dir():
            return []

        sessions: set[date] = set()
        for path in partition_dir.glob(f"{prefix}*{PARTITION_SUFFIX}"):
            ref = PartitionRef(
                dataset_id=self._namespace,
                table_name="daily",
                partition_key=path.stem,
                uri=str(path),
                row_count=0,
                content_hash="",
            )
            for row in read_partition(ref):
                sessions.add(date.fromisoformat(str(row["session"])))
        return sorted(sessions)

    def get_bars(
        self,
        instrument_id: InstrumentId,
        start_date: date,
        end_date: date,
        semantic: BarPriceSemantic = BarPriceSemantic.RAW,
    ) -> tuple[MarketBar, ...]:
        inst_str = str(instrument_id.value)
        start_str = start_date.isoformat()
        end_str = end_date.isoformat()

        # Partitions are already keyed by instrument, semantic, and year, so the only
        # work left is a date-range filter. Routing that through the generic SQL store
        # would rebuild an in-memory table and re-insert every row on each call, which
        # dominates the runtime of a long study that reads bars once per rebalance.
        rows: list[dict[str, object]] = []
        for year in range(start_date.year, end_date.year + 1):
            pkey = self._partition_key(instrument_id, semantic, year)
            part_path = (
                self._store.base_dir / self._namespace / "daily" / f"{pkey}{PARTITION_SUFFIX}"
            )
            if not part_path.exists():
                continue

            ref = PartitionRef(
                dataset_id=self._namespace,
                table_name="daily",
                partition_key=pkey,
                uri=str(part_path),
                row_count=0,
                content_hash="",
            )
            rows.extend(
                row
                for row in read_partition(ref)
                if start_str <= str(row["session"]) <= end_str
                and str(row["instrument_id"]) == inst_str
            )

        if not rows:
            return ()

        rows.sort(key=lambda r: str(r["session"]))

        bars = [
            MarketBar(
                instrument_id=InstrumentId.from_uuid(UUID(str(r["instrument_id"]))),
                session=date.fromisoformat(str(r["session"])),
                observed_at=datetime.fromisoformat(str(r["observed_at"])).replace(tzinfo=UTC),
                open=Decimal(str(r["open"])),
                high=Decimal(str(r["high"])),
                low=Decimal(str(r["low"])),
                close=Decimal(str(r["close"])),
                volume=Decimal(str(r["volume"])),
                semantic=BarPriceSemantic(str(r["semantic"])),
                source=str(r["source"]),
            )
            for r in rows
        ]
        return tuple(bars)
