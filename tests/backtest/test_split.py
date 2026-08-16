"""Tests for stock split accounting and value conservation."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from quantlab.backtest.accounting import AccountingEngine
from quantlab.domain.corporate_actions import CorporateAction, CorporateActionType
from quantlab.domain.identity import InstrumentId
from quantlab.domain.orders import Fill, OrderSide


def test_stock_split_conserves_position_value() -> None:
    now = datetime(2026, 1, 2, 14, 30, tzinfo=UTC)
    inst = InstrumentId(uuid.UUID(int=1))

    engine = AccountingEngine(initial_cash=Decimal("100000.00"))

    # Buy 100 shares @ $100 -> Cost basis $100, Total cost $10,000
    buy_fill = Fill(
        fill_id="FILL-01",
        order_id="ORD-01",
        instrument_id=inst,
        filled_at=now,
        quantity=Decimal("100.0"),
        price=Decimal("100.00"),
        fees=Decimal("0.00"),
        source="test",
    )
    engine.apply_fill(buy_fill, OrderSide.BUY)

    # 2-for-1 split (ratio=2.0)
    split_action = CorporateAction(
        instrument_id=inst,
        action_type=CorporateActionType.SPLIT,
        effective_at=date(2026, 1, 5),
        announced_at=now,
        available_at=now,
        ratio=Decimal("2.0"),
        cash_amount=None,
        source="test",
    )
    engine.apply_corporate_action(split_action, effective_time=now)

    lot = engine.position_ledger.positions[inst]
    # Shares doubled to 200, Cost basis halved to $50
    assert lot.quantity == Decimal("200.0")
    assert lot.cost_basis_per_share == Decimal("50.0")
    # Total cost conserved at $10,000
    assert lot.total_cost == Decimal("10000.00")
