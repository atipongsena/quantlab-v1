from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from quantlab.domain.identity import InstrumentId
from quantlab.domain.market import BarPriceSemantic, MarketBar
from quantlab.infrastructure.duckdb import LocalAnalyticalStore


class MarketBarStore:
    def __init__(self, analytical_store: LocalAnalyticalStore) -> None:
        self._store = analytical_store

    def write_daily_bars(self, bars: Sequence[MarketBar]) -> None:
        if not bars:
            return

        # Group bars by instrument and year for partitioning
        by_partition: dict[str, list[dict[str, object]]] = {}
        for bar in bars:
            key = f"{bar.instrument_id.value}_{bar.session.year}"
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
                dataset_id="market_bars",
                table="daily",
                partition_key=partition_key,
                data=rows,
            )

    def get_bars(
        self,
        instrument_id: InstrumentId,
        start_date: date,
        end_date: date,
        semantic: BarPriceSemantic = BarPriceSemantic.RAW,
    ) -> tuple[MarketBar, ...]:
        inst_str = str(instrument_id.value)
        # Find relevant partitions
        years = range(start_date.year, end_date.year + 1)
        partition_keys = [f"{inst_str}_{yr}" for yr in years]

        refs = []
        for pkey in partition_keys:
            part_path = self._store.base_dir / "market_bars" / "daily" / f"{pkey}.parquet"
            if part_path.exists():
                from quantlab.infrastructure.parquet import PartitionRef

                refs.append(
                    PartitionRef(
                        dataset_id="market_bars",
                        table_name="daily",
                        partition_key=pkey,
                        uri=str(part_path),
                        row_count=0,
                        content_hash="",
                    )
                )

        if not refs:
            return ()

        query = """
        SELECT instrument_id, session, observed_at, open, high, low, close, volume, semantic, source
        FROM daily
        WHERE instrument_id = ?
          AND session >= ? AND session <= ?
          AND semantic = ?
        ORDER BY session ASC
        """
        rows = self._store.query(
            query,
            params=[inst_str, start_date.isoformat(), end_date.isoformat(), semantic.value],
            refs=refs,
        )

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
