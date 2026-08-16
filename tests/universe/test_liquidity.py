from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

from quantlab.domain.identity import InstrumentId
from quantlab.domain.market import BarPriceSemantic, MarketBar
from quantlab.universe.liquidity import LiquidityFilter


def _make_bar(inst_id: InstrumentId, d: date, price: Decimal, volume: Decimal) -> MarketBar:
    return MarketBar(
        instrument_id=inst_id,
        session=d,
        observed_at=datetime(d.year, d.month, d.day, 21, 0, tzinfo=UTC),
        open=price,
        high=price,
        low=price,
        close=price,
        volume=volume,
        semantic=BarPriceSemantic.RAW,
        source="test",
    )


def test_liquidity_filter_median_dollar_volume_cutoff() -> None:
    liquid_id = InstrumentId.from_uuid(uuid4())
    illiquid_id = InstrumentId.from_uuid(uuid4())

    # Liquid instrument: price $100, volume 50,000 -> dollar volume $5,000,000/day
    liquid_bars = [
        _make_bar(liquid_id, date(2020, 1, day), Decimal("100.0"), Decimal("50000"))
        for day in range(2, 10)
    ]

    # Illiquid instrument: price $10, volume 1,000 -> dollar volume $10,000/day
    illiquid_bars = [
        _make_bar(illiquid_id, date(2020, 1, day), Decimal("10.0"), Decimal("1000"))
        for day in range(2, 10)
    ]

    bars_map = {
        liquid_id: liquid_bars,
        illiquid_id: illiquid_bars,
    }

    # Threshold $1,000,000 median dollar volume
    liq_filter = LiquidityFilter(
        min_median_dollar_volume=Decimal("1000000"),
        min_bar_count=5,
    )

    filtered = liq_filter.filter_liquid(bars_map)
    assert liquid_id in filtered
    assert illiquid_id not in filtered
