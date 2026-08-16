"""Tests for TradeBreak severity classification."""

from decimal import Decimal

from quantlab.paper.breaks import BreakSeverity, BreakType
from quantlab.paper.contracts import BrokerAccount
from quantlab.paper.reconciliation import ShadowReconciler


def test_cash_break_critical_threshold() -> None:
    broker = BrokerAccount("ACCT-01", Decimal("90000.00"), Decimal("90000.00"), {})
    rep = ShadowReconciler.reconcile(Decimal("100000.00"), {}, broker)

    assert not rep.is_clean
    assert rep.max_severity == BreakSeverity.CRITICAL
    assert rep.breaks[0].break_type == BreakType.CASH_MISMATCH
    assert rep.breaks[0].difference == Decimal("10000.00")
