"""Tests for disaster recovery replay."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from quantlab.domain.identity import InstrumentId
from quantlab.paper.contracts import PaperFill, PaperOrderSide
from quantlab.paper.recovery import DisasterRecoveryEngine


def test_disaster_recovery_reconstructs_exact_state() -> None:
    inst1 = InstrumentId(uuid.UUID(int=1))
    f1 = PaperFill(
        fill_id="F1",
        order_id="O1",
        instrument_id=inst1,
        side=PaperOrderSide.BUY,
        quantity=100,
        price=Decimal("50.00"),
        commission=Decimal("1.00"),
        filled_at=datetime(2026, 1, 5, 9, 30, tzinfo=UTC),
    )
    f2 = PaperFill(
        fill_id="F2",
        order_id="O2",
        instrument_id=inst1,
        side=PaperOrderSide.SELL,
        quantity=40,
        price=Decimal("60.00"),
        commission=Decimal("1.00"),
        filled_at=datetime(2026, 1, 5, 15, 30, tzinfo=UTC),
    )

    account = DisasterRecoveryEngine.reconstruct_from_fills(
        account_id="PAPER-RECOVER",
        initial_cash=Decimal("10000.00"),
        fills=[f1, f2],
    )

    # Cash: 10000 - (100 * 50 + 1) + (40 * 60 - 1) = 10000 - 5001 + 2399 = 7398.00
    assert account.cash_balance == Decimal("7398.00")
    # Position: 100 - 40 = 60 shares
    assert account.positions[inst1] == Decimal("60")
