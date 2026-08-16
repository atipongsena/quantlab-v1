"""Authoritative validation verdicts and decision policy."""

from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum

from quantlab.validation.gates import GateDecision
from quantlab.validation.multiple_testing import MultipleTestingEvidence
from quantlab.validation.robustness import RobustnessArtifact


class ValidationVerdict(StrEnum):
    REJECTED = "REJECTED"
    RESEARCH_ONLY = "RESEARCH_ONLY"
    VALIDATED = "VALIDATED"
    PAPER_CANDIDATE = "PAPER_CANDIDATE"


class VerdictEngine:
    """Computes authoritative validation verdicts from hard gates and statistical evidence."""

    @classmethod
    def determine_verdict(
        cls,
        hard_gates: Sequence[GateDecision],
        robustness: RobustnessArtifact,
        multiple_testing: MultipleTestingEvidence,
        is_paper_eligible: bool = True,
    ) -> tuple[ValidationVerdict, list[str]]:
        reasons: list[str] = []

        # 1. Any hard gate failure forces REJECTED
        failed_gates = [g for g in hard_gates if not g.passed]
        if failed_gates:
            for g in failed_gates:
                reasons.append(f"Hard gate failed: {g.gate_type} ({g.reason})")
            return ValidationVerdict.REJECTED, reasons

        # 2. Check soft robustness criteria
        is_fragile = robustness.cost_stress.is_cost_fragile
        is_concentrated = robustness.concentration.is_excessively_concentrated

        if is_fragile:
            reasons.append(
                f"Cost fragile: break-even friction is only "
                f"{robustness.cost_stress.break_even_cost_bps} bps"
            )
        if is_concentrated:
            reasons.append(
                f"Excessive concentration: HHI is {robustness.concentration.herfindahl_index}"
            )
        if multiple_testing.is_multiple_testing_warned:
            reasons.append(
                f"Multiple testing warning: evaluated {multiple_testing.n_trials} trials "
                f"(DSR p-value: {multiple_testing.deflated_sharpe_p_value})"
            )

        if is_fragile or is_concentrated or multiple_testing.is_multiple_testing_warned:
            return ValidationVerdict.RESEARCH_ONLY, reasons

        # 3. If all criteria clean -> VALIDATED or PAPER_CANDIDATE
        if is_paper_eligible:
            return (
                ValidationVerdict.PAPER_CANDIDATE,
                ["Passed all hard gates and robustness requirements"],
            )

        return (
            ValidationVerdict.VALIDATED,
            ["Passed all hard gates and robustness requirements"],
        )
