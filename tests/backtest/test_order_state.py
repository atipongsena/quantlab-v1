"""Tests for OrderStateMachine transition rules."""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from quantlab.backtest.order_state import OrderStateMachine
from quantlab.domain.identity import InstrumentId
from quantlab.domain.orders import Order, OrderSide, OrderState, OrderType


def test_order_state_transitions() -> None:
    now = datetime(2026, 1, 1, 14, 30, tzinfo=UTC)
    inst = InstrumentId(uuid.UUID(int=1))

    order = Order(
        order_id="ORD-01",
        instrument_id=inst,
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=Decimal("100.0"),
        state=OrderState.CREATED,
        created_at=now,
    )

    t1 = now + timedelta(seconds=1)
    submitted = OrderStateMachine.transition(order, OrderState.SUBMITTED, transitioned_at=t1)
    assert submitted.state == OrderState.SUBMITTED

    t2 = now + timedelta(seconds=2)
    filled = OrderStateMachine.transition(submitted, OrderState.FILLED, transitioned_at=t2)
    assert filled.state == OrderState.FILLED

    # Transitioning from terminal state FILLED to CANCELLED must fail
    t3 = now + timedelta(seconds=3)
    with pytest.raises(ValueError, match="terminal order state cannot transition"):
        OrderStateMachine.transition(filled, OrderState.CANCELLED, transitioned_at=t3)
