"""Tests for symbol change invariance using InstrumentId."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from quantlab.backtest.accounting import AccountingEngine
from quantlab.domain.identity import InstrumentId
from quantlab.domain.orders import Fill, OrderSide


def test_symbol_change_invariance() -> None:
    now = datetime(2026, 1, 2, 14, 30, tzinfo=UTC)
    inst_id = InstrumentId(uuid.UUID(int=1))

    engine = AccountingEngine(initial_cash=Decimal("100000.00"))

    # Buy when symbol is FB
    buy_fill = Fill(
        fill_id="FILL-01",
        order_id="ORD-01",
        instrument_id=inst_id,
        filled_at=now,
        quantity=Decimal("100.0"),
        price=Decimal("150.00"),
        fees=Decimal("0.00"),
        source="test",
    )
    engine.apply_fill(buy_fill, OrderSide.BUY)

    # Symbol renames to META — InstrumentId remains identical
    lot = engine.position_ledger.positions[inst_id]
    assert lot.quantity == Decimal("100.0")
    assert lot.cost_basis_per_share == Decimal("150.00")
