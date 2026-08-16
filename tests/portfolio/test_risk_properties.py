"""Tests for RiskEngine properties and convergence."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from quantlab.domain.identity import InstrumentId
from quantlab.domain.portfolio import TargetPortfolio, TargetPosition
from quantlab.portfolio.constraints import ConstraintStatus
from quantlab.portfolio.risk import RiskEngine, RiskSpec


def test_risk_engine_convergence_and_adjustment() -> None:
    now = datetime(2026, 1, 1, 16, 0, tzinfo=UTC)
    insts = [InstrumentId(uuid.UUID(int=i + 1)) for i in range(10)]

    # 10 instruments with 10% weight each (exceeds 5% name cap)
    positions = tuple(
        TargetPosition(instrument_id=inst, target_weight=Decimal("0.10"), target_quantity=None)
        for inst in insts
    )
    target = TargetPortfolio(
        portfolio_id="PORT-001",
        decision_time=now,
        positions=positions,
        source_alpha_snapshot_id="hash123",
    )

    spec = RiskSpec(max_name_weight=Decimal("0.05"), gross_exposure_cap=Decimal("1.0"))
    engine = RiskEngine(spec)
    decision = engine.apply(target)

    assert decision.status == ConstraintStatus.ADJUST
    assert len(decision.adjusted_target.positions) == 10
    for pos in decision.adjusted_target.positions:
        assert pos.target_weight <= Decimal("0.05")
