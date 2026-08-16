"""Tests for volume participation limits and partial fills."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from quantlab.backtest.broker import SimulatedBroker
from quantlab.backtest.participation import VolumeParticipationModel
from quantlab.domain.identity import InstrumentId
from quantlab.domain.market import BarPriceSemantic, MarketBar
from quantlab.domain.orders import Order, OrderSide, OrderState, OrderType


def test_participation_limit_generates_partial_fill() -> None:
    inst = InstrumentId(uuid.UUID(int=1))
    session = date(2026, 1, 2)
    t_open = datetime(2026, 1, 2, 14, 30, tzinfo=UTC)

    # Total bar volume = 10,000 shares
    bar = MarketBar(
        instrument_id=inst,
        session=session,
        observed_at=t_open,
        open=Decimal("50.00"),
        high=Decimal("51.00"),
        low=Decimal("49.00"),
        close=Decimal("50.50"),
        volume=Decimal("10000"),
        semantic=BarPriceSemantic.RAW,
        source="test",
    )

    # Order wants 2,000 shares
    order = Order(
        order_id="ORD-01",
        instrument_id=inst,
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=Decimal("2000.0"),
        state=OrderState.CREATED,
        created_at=datetime(2026, 1, 1, 21, 5, tzinfo=UTC),
    )

    # 10% max participation -> max 1,000 shares
    broker = SimulatedBroker(
        participation_model=VolumeParticipationModel(max_participation_pct=Decimal("0.10"))
    )

    updated_order, fill = broker.execute_order(order, bar, session, t_open)

    assert updated_order.state == OrderState.PARTIALLY_FILLED
    assert fill is not None
    assert fill.quantity == Decimal("1000.0")
