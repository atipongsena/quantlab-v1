"""Tests for delisting settlement accounting."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from quantlab.backtest.accounting import AccountingEngine
from quantlab.domain.corporate_actions import CorporateAction, CorporateActionType
from quantlab.domain.identity import InstrumentId
from quantlab.domain.orders import Fill, OrderSide


def test_delisting_liquidation_settlement() -> None:
    now = datetime(2026, 1, 2, 14, 30, tzinfo=UTC)
    inst = InstrumentId(uuid.UUID(int=1))

    engine = AccountingEngine(initial_cash=Decimal("100000.00"))

    # Buy 100 shares @ $100 -> Cash: $90,000
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

    # Delisting with $10 liquidation price -> proceeds $1,000, Realized loss = -$9,000
    delist_action = CorporateAction(
        instrument_id=inst,
        action_type=CorporateActionType.DELISTING,
        effective_at=date(2026, 1, 5),
        announced_at=now,
        available_at=now,
        ratio=None,
        cash_amount=Decimal("10.00"),
        source="test",
    )
    engine.apply_corporate_action(delist_action, effective_time=now)

    assert engine.position_ledger.get_quantity(inst) == Decimal("0.0")
    assert engine.cash_ledger.balance == Decimal("91000.00")
    assert engine.position_ledger.total_realized_pnl == Decimal("-9000.00")
