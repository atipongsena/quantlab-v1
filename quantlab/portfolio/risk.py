"""Risk engine for pre-trade constraint verification and portfolio adjustments."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal

from quantlab.domain.identity import InstrumentId
from quantlab.domain.portfolio import TargetPortfolio, TargetPosition
from quantlab.portfolio.constraints import (
    ConstraintResult,
    ConstraintStatus,
    GrossExposureConstraint,
    MaxNameWeightConstraint,
    MaxSectorWeightConstraint,
)


@dataclass(frozen=True, slots=True)
class RiskSpec:
    """Pre-trade risk configuration parameters."""

    max_name_weight: Decimal = Decimal("0.05")
    max_sector_weight: Decimal = Decimal("0.30")
    max_unknown_sector_weight: Decimal = Decimal("0.10")
    gross_exposure_cap: Decimal = Decimal("1.00")
    min_cash_buffer_pct: Decimal = Decimal("0.01")
    max_adv_participation: Decimal = Decimal("0.10")
    no_trade_band_pct: Decimal = Decimal("0.005")
    min_trade_dollar: Decimal = Decimal("100.0")
    max_turnover_pct: Decimal = Decimal("0.50")
    max_iterations: int = 10


@dataclass(frozen=True, slots=True)
class RiskDecision:
    """Outcome of risk engine evaluation."""

    status: ConstraintStatus
    adjusted_target: TargetPortfolio
    results: tuple[ConstraintResult, ...]
    violations: tuple[str, ...] = field(default_factory=tuple)


class RiskEngine:
    """Enforces pre-trade risk constraints in deterministic order."""

    def __init__(self, spec: RiskSpec | None = None) -> None:
        self._spec = spec or RiskSpec()

    def apply(
        self,
        target: TargetPortfolio,
        sectors: Mapping[InstrumentId, str] | None = None,
    ) -> RiskDecision:
        current_weights = {p.instrument_id: p.target_weight for p in target.positions}
        if not current_weights:
            return RiskDecision(
                status=ConstraintStatus.PASS,
                adjusted_target=target,
                results=(),
                violations=(),
            )

        name_constraint = MaxNameWeightConstraint(self._spec.max_name_weight)
        sector_constraint = MaxSectorWeightConstraint(
            self._spec.max_sector_weight, self._spec.max_unknown_sector_weight
        )
        gross_constraint = GrossExposureConstraint(
            self._spec.gross_exposure_cap, self._spec.min_cash_buffer_pct
        )

        all_results: list[ConstraintResult] = []
        weights = dict(current_weights)

        # Iteratively apply constraints up to max_iterations to handle cross-constraint interactions
        for iteration in range(self._spec.max_iterations):
            w1, r1 = name_constraint.apply(weights)
            w2, r2 = sector_constraint.apply(w1, sectors)
            w3, r3 = gross_constraint.apply(w2)

            if iteration == 0:
                all_results.extend([r1, r2, r3])

            if w3 == weights:
                break
            weights = w3
        else:
            # If not converged after max_iterations
            return RiskDecision(
                status=ConstraintStatus.REJECT,
                adjusted_target=target,
                results=tuple(all_results),
                violations=("Risk constraints did not converge within max iterations",),
            )

        # Determine overall status
        statuses = [r.status for r in all_results]
        overall_status = ConstraintStatus.PASS
        if ConstraintStatus.REJECT in statuses:
            overall_status = ConstraintStatus.REJECT
        elif ConstraintStatus.ADJUST in statuses:
            overall_status = ConstraintStatus.ADJUST

        # Build adjusted target portfolio (sorted by instrument id for determinism)
        sorted_insts = sorted(weights.keys(), key=lambda inst: str(inst.value))
        adjusted_positions = tuple(
            TargetPosition(
                instrument_id=inst,
                target_weight=weights[inst],
                target_quantity=None,
            )
            for inst in sorted_insts
            if weights[inst] > Decimal("0.0")
        )

        adjusted_portfolio = TargetPortfolio(
            portfolio_id=target.portfolio_id,
            decision_time=target.decision_time,
            positions=adjusted_positions,
            source_alpha_snapshot_id=target.source_alpha_snapshot_id,
        )

        return RiskDecision(
            status=overall_status,
            adjusted_target=adjusted_portfolio,
            results=tuple(all_results),
            violations=(),
        )
