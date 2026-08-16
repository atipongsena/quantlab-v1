from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from quantlab.data.market_bars import MarketBarStore
from quantlab.domain.identity import InstrumentId
from quantlab.domain.market import BarPriceSemantic, MarketBar
from quantlab.infrastructure.duckdb import LocalAnalyticalStore


def test_market_bar_store_roundtrip_and_semantics(tmp_path: Path) -> None:
    analytical_store = LocalAnalyticalStore(tmp_path)
    bar_store = MarketBarStore(analytical_store)

    inst_id = InstrumentId.from_uuid(uuid4())

    raw_bar1 = MarketBar(
        instrument_id=inst_id,
        session=date(2020, 1, 2),
        observed_at=datetime(2020, 1, 2, 21, 0, tzinfo=UTC),
        open=Decimal("100.0"),
        high=Decimal("105.0"),
        low=Decimal("99.0"),
        close=Decimal("104.0"),
        volume=Decimal("1000000"),
        semantic=BarPriceSemantic.RAW,
        source="test",
    )
    raw_bar2 = MarketBar(
        instrument_id=inst_id,
        session=date(2020, 1, 3),
        observed_at=datetime(2020, 1, 3, 21, 0, tzinfo=UTC),
        open=Decimal("104.0"),
        high=Decimal("108.0"),
        low=Decimal("103.0"),
        close=Decimal("107.0"),
        volume=Decimal("1200000"),
        semantic=BarPriceSemantic.RAW,
        source="test",
    )
    adj_bar1 = MarketBar(
        instrument_id=inst_id,
        session=date(2020, 1, 2),
        observed_at=datetime(2020, 1, 2, 21, 0, tzinfo=UTC),
        open=Decimal("25.0"),
        high=Decimal("26.25"),
        low=Decimal("24.75"),
        close=Decimal("26.0"),
        volume=Decimal("4000000"),
        semantic=BarPriceSemantic.ADJUSTED,
        source="test:adjusted",
    )

    bar_store.write_daily_bars([raw_bar1, raw_bar2, adj_bar1])

    # Query RAW
    raw_retrieved = bar_store.get_bars(
        inst_id, date(2020, 1, 1), date(2020, 1, 5), BarPriceSemantic.RAW
    )
    assert len(raw_retrieved) == 2
    assert raw_retrieved[0].close == Decimal("104.0")
    assert raw_retrieved[1].close == Decimal("107.0")

    # Query ADJUSTED
    adj_retrieved = bar_store.get_bars(
        inst_id, date(2020, 1, 1), date(2020, 1, 5), BarPriceSemantic.ADJUSTED
    )
    assert len(adj_retrieved) == 1
    assert adj_retrieved[0].close == Decimal("26.0")
