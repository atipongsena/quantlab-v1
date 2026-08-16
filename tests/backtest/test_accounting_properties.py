"""Property tests for accounting conservation."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from quantlab.backtest.accounting import AccountingEngine
from quantlab.domain.identity import InstrumentId
from quantlab.domain.orders import Fill, OrderSide


def test_multi_fill_mark_to_market_conservation() -> None:
    now = datetime(2026, 1, 2, 14, 30, tzinfo=UTC)
    inst1 = InstrumentId(uuid.UUID(int=1))
    inst2 = InstrumentId(uuid.UUID(int=2))

    engine = AccountingEngine(initial_cash=Decimal("500000.00"))

    # Buy inst1: 1,000 shares @ $100 + $5 fee = -$100,005
    engine.apply_fill(
        Fill("F1", "O1", inst1, now, Decimal("1000.0"), Decimal("100.00"), Decimal("5.00"), "test"),
        OrderSide.BUY,
    )

    # Buy inst2: 2,000 shares @ $50 + $5 fee = -$100,005
    engine.apply_fill(
        Fill("F2", "O2", inst2, now, Decimal("2000.0"), Decimal("50.00"), Decimal("5.00"), "test"),
        OrderSide.BUY,
    )

    # Cash = 500,000 - 200,010 = 299,990.00
    assert engine.cash_ledger.balance == Decimal("299990.00")

    # Mark to market: inst1 close = $110, inst2 close = $45
    close_prices = {inst1: Decimal("110.00"), inst2: Decimal("45.00")}
    snapshot = engine.mark_to_market(now, close_prices)

    assert snapshot.cash == Decimal("299990.00")
    assert len(snapshot.positions) == 2

    # Total portfolio equity = Cash (299,990) + Pos1 (110,000) + Pos2 (90,000) = $499,990.00
    total_equity = snapshot.cash + sum(p.market_value for p in snapshot.positions)
    assert total_equity == Decimal("499990.00")
