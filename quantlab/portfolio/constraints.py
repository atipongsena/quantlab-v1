"""Portfolio risk constraints with structured audit diagnostics."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from quantlab.domain.identity import InstrumentId


class ConstraintStatus(StrEnum):
    PASS = "pass"
    ADJUST = "adjust"
    REJECT = "reject"


@dataclass(frozen=True, slots=True)
class ConstraintResult:
    name: str
    status: ConstraintStatus
    reason: str
    before_value: object
    after_value: object


class MaxNameWeightConstraint:
    """Caps individual asset weights at a specified maximum percentage."""

    def __init__(self, max_weight: Decimal = Decimal("0.05")) -> None:
        self._max_weight = max_weight

    def apply(
        self, weights: Mapping[InstrumentId, Decimal]
    ) -> tuple[dict[InstrumentId, Decimal], ConstraintResult]:
        adjusted = dict(weights)
        violations = False

        for inst, w in adjusted.items():
            if w > self._max_weight:
                adjusted[inst] = self._max_weight
                violations = True

        status = ConstraintStatus.ADJUST if violations else ConstraintStatus.PASS
        reason = (
            "Capped weights exceeding max_name_weight" if violations else "All weights within limit"
        )

        return adjusted, ConstraintResult(
            name="max_name_weight",
            status=status,
            reason=reason,
            before_value=dict(weights),
            after_value=adjusted,
        )


class MaxSectorWeightConstraint:
    """Caps aggregate portfolio weight in any single industry sector."""

    def __init__(
        self,
        max_sector_weight: Decimal = Decimal("0.30"),
        max_unknown_sector_weight: Decimal = Decimal("0.10"),
    ) -> None:
        self._max_sector_weight = max_sector_weight
        self._max_unknown_sector_weight = max_unknown_sector_weight

    def apply(
        self,
        weights: Mapping[InstrumentId, Decimal],
        sectors: Mapping[InstrumentId, str] | None = None,
    ) -> tuple[dict[InstrumentId, Decimal], ConstraintResult]:
        if not sectors:
            return dict(weights), ConstraintResult(
                name="max_sector_weight",
                status=ConstraintStatus.PASS,
                reason="No sector mapping provided",
                before_value=dict(weights),
                after_value=dict(weights),
            )

        sector_weights: dict[str, Decimal] = {}
        for inst, w in weights.items():
            sec = sectors.get(inst, "UNKNOWN")
            sector_weights[sec] = sector_weights.get(sec, Decimal("0.0")) + w

        adjusted = dict(weights)
        violations = False

        for sec, total_w in sector_weights.items():
            cap = self._max_unknown_sector_weight if sec == "UNKNOWN" else self._max_sector_weight
            if total_w > cap:
                scale = cap / total_w
                for inst, w in weights.items():
                    if sectors.get(inst, "UNKNOWN") == sec:
                        adjusted[inst] = (w * scale).quantize(Decimal("0.000001"))
                violations = True

        status = ConstraintStatus.ADJUST if violations else ConstraintStatus.PASS
        reason = (
            "Scaled down sectors exceeding sector limit"
            if violations
            else "All sectors within limit"
        )

        return adjusted, ConstraintResult(
            name="max_sector_weight",
            status=status,
            reason=reason,
            before_value=sector_weights,
            after_value=adjusted,
        )


class GrossExposureConstraint:
    """Ensures total gross equity exposure does not exceed capacity and maintains cash buffer."""

    def __init__(
        self,
        gross_cap: Decimal = Decimal("1.0"),
        min_cash_buffer_pct: Decimal = Decimal("0.01"),
    ) -> None:
        self._gross_cap = gross_cap
        self._min_cash_buffer_pct = min_cash_buffer_pct

    def apply(
        self, weights: Mapping[InstrumentId, Decimal]
    ) -> tuple[dict[InstrumentId, Decimal], ConstraintResult]:
        total_w = sum(weights.values(), Decimal("0.0"))
        max_allowed = (self._gross_cap - self._min_cash_buffer_pct).quantize(Decimal("0.000001"))

        if total_w <= max_allowed:
            return dict(weights), ConstraintResult(
                name="gross_exposure",
                status=ConstraintStatus.PASS,
                reason="Gross exposure within limit",
                before_value=total_w,
                after_value=total_w,
            )

        scale = max_allowed / total_w
        adjusted = {inst: (w * scale).quantize(Decimal("0.000001")) for inst, w in weights.items()}

        return adjusted, ConstraintResult(
            name="gross_exposure",
            status=ConstraintStatus.ADJUST,
            reason=f"Gross exposure {total_w} scaled down to {max_allowed}",
            before_value=total_w,
            after_value=sum(adjusted.values()),
        )
