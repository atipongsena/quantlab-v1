"""Tests for operational fault handling, disconnections, and break detections."""

import uuid
from decimal import Decimal

from quantlab.domain.identity import InstrumentId
from quantlab.paper.breaks import BreakSeverity
from quantlab.paper.contracts import BrokerAccount
from quantlab.paper.reconciliation import ShadowReconciler


def test_reconciliation_handles_corrupt_broker_data() -> None:
    inst1 = InstrumentId(uuid.UUID(int=1))
    shadow_positions = {inst1: Decimal("100")}
    # Simulating broker reporting negative or corrupt position
    corrupt_broker = BrokerAccount(
        "ACCT-01", Decimal("0.00"), Decimal("0.00"), {inst1: Decimal("-50")}
    )

    rep = ShadowReconciler.reconcile(Decimal("50000.00"), shadow_positions, corrupt_broker)
    assert not rep.is_clean
    assert rep.max_severity == BreakSeverity.CRITICAL
    assert len(rep.breaks) >= 2  # cash mismatch + position mismatch
