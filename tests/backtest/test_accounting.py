"""Tests for core portfolio accounting and buy/sell roundtrip."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from quantlab.backtest.accounting import AccountingEngine
from quantlab.domain.identity import InstrumentId
from quantlab.domain.orders import Fill, OrderSide


def test_accounting_buy_and_sell_roundtrip() -> None:
    now = datetime(2026, 1, 2, 14, 30, tzinfo=UTC)
    inst = InstrumentId(uuid.UUID(int=1))

    engine = AccountingEngine(initial_cash=Decimal("100000.00"))

    # Buy 100 shares @ $100 with $1 fee -> Cash: $100,000 - $10,001 = $89,999
    buy_fill = Fill(
        fill_id="FILL-01",
        order_id="ORD-01",
        instrument_id=inst,
        filled_at=now,
        quantity=Decimal("100.0"),
        price=Decimal("100.00"),
        fees=Decimal("1.00"),
        source="test",
    )
    engine.apply_fill(buy_fill, OrderSide.BUY)

    assert engine.cash_ledger.balance == Decimal("89999.00")
    assert engine.position_ledger.get_quantity(inst) == Decimal("100.0")

    # Sell 100 shares @ $110 with $1 fee -> Gross proceeds $11,000, Net $10,999
    # Realized PnL = 100 * ($110 - $100) = $1,000
    # Final cash = $89,999 + $10,999 = $100,998
    sell_fill = Fill(
        fill_id="FILL-02",
        order_id="ORD-02",
        instrument_id=inst,
        filled_at=now,
        quantity=Decimal("100.0"),
        price=Decimal("110.00"),
        fees=Decimal("1.00"),
        source="test",
    )
    engine.apply_fill(sell_fill, OrderSide.SELL)

    assert engine.cash_ledger.balance == Decimal("100998.00")
    assert engine.position_ledger.get_quantity(inst) == Decimal("0.0")
    assert engine.position_ledger.total_realized_pnl == Decimal("1000.00")
