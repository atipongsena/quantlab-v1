"""Tests for mock execution broker adapter."""

import uuid
from datetime import date
from decimal import Decimal

from quantlab.domain.identity import InstrumentId
from quantlab.paper.adapter import MockExecutionAdapter
from quantlab.paper.contracts import PaperOrder, PaperOrderSide, PaperOrderStatus


def test_mock_broker_adapter_order_execution() -> None:
    adapter = MockExecutionAdapter(initial_cash=Decimal("100000.00"))
    inst = InstrumentId(uuid.UUID(int=1))
    adapter.set_prices({inst: Decimal("50.00")})

    order = PaperOrder(
        order_id="ORD-001",
        session=date(2026, 1, 5),
        instrument_id=inst,
        side=PaperOrderSide.BUY,
        quantity=100,
    )

    filled_order, fills = adapter.submit_order(order)
    assert filled_order.status == PaperOrderStatus.FILLED
    assert len(fills) == 1
    assert fills[0].quantity == 100
    assert fills[0].price > Decimal("50.00")  # 5 bps adverse slippage

    account = adapter.get_account()
    assert account.positions[inst] == Decimal("100")
    assert account.cash_balance < Decimal("95000.00")
