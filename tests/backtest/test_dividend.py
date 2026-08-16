"""Tests for cash dividend accounting."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from quantlab.backtest.accounting import AccountingEngine
from quantlab.domain.corporate_actions import CorporateAction, CorporateActionType
from quantlab.domain.identity import InstrumentId
from quantlab.domain.orders import Fill, OrderSide


def test_cash_dividend_credits_cash_balance() -> None:
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

    # Cash dividend: $2.50 per share -> Total dividend = $250.00
    div_action = CorporateAction(
        instrument_id=inst,
        action_type=CorporateActionType.DIVIDEND,
        effective_at=date(2026, 1, 5),
        announced_at=now,
        available_at=now,
        ratio=None,
        cash_amount=Decimal("2.50"),
        source="test",
    )
    engine.apply_corporate_action(div_action, effective_time=now)

    # Cash should be $90,000 + $250 = $90,250.00
    assert engine.cash_ledger.balance == Decimal("90250.00")
