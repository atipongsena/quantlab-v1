"""Tests for missing market open handling and order rejection."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from quantlab.backtest.broker import SimulatedBroker
from quantlab.domain.identity import InstrumentId
from quantlab.domain.orders import Order, OrderSide, OrderState, OrderType


def test_missing_bar_rejects_order() -> None:
    inst = InstrumentId(uuid.UUID(int=1))
    session = date(2026, 1, 2)
    t_open = datetime(2026, 1, 2, 14, 30, tzinfo=UTC)

    order = Order(
        order_id="ORD-01",
        instrument_id=inst,
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=Decimal("100.0"),
        state=OrderState.CREATED,
        created_at=datetime(2026, 1, 1, 21, 5, tzinfo=UTC),
    )

    broker = SimulatedBroker()
    updated_order, fill = broker.execute_order(order, None, session, t_open)

    assert updated_order.state == OrderState.REJECTED
    assert fill is None


def test_none_bar_rejects_order() -> None:
    inst = InstrumentId(uuid.UUID(int=1))
    session = date(2026, 1, 2)
    t_open = datetime(2026, 1, 2, 14, 30, tzinfo=UTC)

    order = Order(
        order_id="ORD-01",
        instrument_id=inst,
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=Decimal("100.0"),
        state=OrderState.CREATED,
        created_at=datetime(2026, 1, 1, 21, 5, tzinfo=UTC),
    )

    broker = SimulatedBroker()
    updated_order, fill = broker.execute_order(order, None, session, t_open)

    assert updated_order.state == OrderState.REJECTED
    assert fill is None
