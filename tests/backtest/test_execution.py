"""Tests for next-open execution and simulated broker fills."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from quantlab.backtest.broker import SimulatedBroker
from quantlab.domain.identity import InstrumentId
from quantlab.domain.market import BarPriceSemantic, MarketBar
from quantlab.domain.orders import Order, OrderSide, OrderState, OrderType


def test_simulated_broker_executes_at_open_with_slippage() -> None:
    inst = InstrumentId(uuid.UUID(int=1))
    session = date(2026, 1, 2)
    t_open = datetime(2026, 1, 2, 14, 30, tzinfo=UTC)

    bar = MarketBar(
        instrument_id=inst,
        session=session,
        observed_at=t_open,
        open=Decimal("100.00"),
        high=Decimal("105.00"),
        low=Decimal("99.00"),
        close=Decimal("104.00"),
        volume=Decimal("1000000"),
        semantic=BarPriceSemantic.RAW,
        source="test",
    )

    # Buy order: 100 shares at open $100.00 with 5 bps slippage = $100.05
    buy_order = Order(
        order_id="ORD-BUY-01",
        instrument_id=inst,
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=Decimal("100.0"),
        state=OrderState.CREATED,
        created_at=datetime(2026, 1, 1, 21, 5, tzinfo=UTC),
    )

    broker = SimulatedBroker()
    updated_order, fill = broker.execute_order(buy_order, bar, session, t_open)

    assert updated_order.state == OrderState.FILLED
    assert fill is not None
    assert fill.price == Decimal("100.0500")
    assert fill.quantity == Decimal("100.0")

    # Sell order: 100 shares at open $100.00 with 5 bps slippage = $99.95
    sell_order = Order(
        order_id="ORD-SELL-01",
        instrument_id=inst,
        side=OrderSide.SELL,
        order_type=OrderType.MARKET,
        quantity=Decimal("100.0"),
        state=OrderState.CREATED,
        created_at=datetime(2026, 1, 1, 21, 5, tzinfo=UTC),
    )

    updated_sell, sell_fill = broker.execute_order(sell_order, bar, session, t_open)
    assert updated_sell.state == OrderState.FILLED
    assert sell_fill is not None
    assert sell_fill.price == Decimal("99.9500")
