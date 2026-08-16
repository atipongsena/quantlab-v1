"""Tests for shadow ledger reconciliation."""

import uuid
from decimal import Decimal

from quantlab.domain.identity import InstrumentId
from quantlab.paper.breaks import BreakSeverity
from quantlab.paper.contracts import BrokerAccount
from quantlab.paper.reconciliation import ShadowReconciler


def test_shadow_reconciliation_clean() -> None:
    inst1 = InstrumentId(uuid.UUID(int=1))
    cash = Decimal("100000.00")
    positions = {inst1: Decimal("500")}

    broker = BrokerAccount("ACCT-01", cash, cash, positions)
    rep = ShadowReconciler.reconcile(cash, positions, broker)

    assert rep.is_clean
    assert rep.max_severity == BreakSeverity.NONE
    assert len(rep.breaks) == 0


def test_shadow_reconciliation_detects_position_break() -> None:
    inst1 = InstrumentId(uuid.UUID(int=1))
    cash = Decimal("100000.00")
    shadow_positions = {inst1: Decimal("500")}
    broker_positions = {inst1: Decimal("400")}  # 100 shares missing

    broker = BrokerAccount("ACCT-01", cash, cash, broker_positions)
    rep = ShadowReconciler.reconcile(cash, shadow_positions, broker)

    assert not rep.is_clean
    assert rep.max_severity == BreakSeverity.CRITICAL
    assert len(rep.breaks) == 1
    assert rep.breaks[0].difference == Decimal("100")
