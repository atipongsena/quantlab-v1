"""Tests for individual portfolio risk constraints."""

import uuid
from decimal import Decimal

from quantlab.domain.identity import InstrumentId
from quantlab.portfolio.constraints import (
    ConstraintStatus,
    GrossExposureConstraint,
    MaxNameWeightConstraint,
    MaxSectorWeightConstraint,
)


def test_max_name_weight_constraint() -> None:
    inst1 = InstrumentId(uuid.uuid4())
    inst2 = InstrumentId(uuid.uuid4())

    weights = {inst1: Decimal("0.08"), inst2: Decimal("0.03")}
    constraint = MaxNameWeightConstraint(max_weight=Decimal("0.05"))

    adjusted, result = constraint.apply(weights)
    assert result.status == ConstraintStatus.ADJUST
    assert adjusted[inst1] == Decimal("0.05")
    assert adjusted[inst2] == Decimal("0.03")


def test_max_sector_weight_constraint() -> None:
    tech_insts = [InstrumentId(uuid.uuid4()) for _ in range(4)]
    weights = {inst: Decimal("0.10") for inst in tech_insts}  # 40% tech
    sectors = {inst: "Technology" for inst in tech_insts}

    constraint = MaxSectorWeightConstraint(max_sector_weight=Decimal("0.30"))
    adjusted, result = constraint.apply(weights, sectors)

    assert result.status == ConstraintStatus.ADJUST
    total_tech = sum(adjusted.values())
    assert total_tech == Decimal("0.30")


def test_gross_exposure_constraint() -> None:
    insts = [InstrumentId(uuid.uuid4()) for _ in range(5)]
    weights = {inst: Decimal("0.25") for inst in insts}  # 125% gross

    constraint = GrossExposureConstraint(
        gross_cap=Decimal("1.0"), min_cash_buffer_pct=Decimal("0.01")
    )
    adjusted, result = constraint.apply(weights)

    assert result.status == ConstraintStatus.ADJUST
    total_w = sum(adjusted.values())
    assert total_w == Decimal("0.99")
