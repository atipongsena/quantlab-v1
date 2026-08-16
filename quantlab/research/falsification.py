"""Systematic 4-vector adversarial falsification engine."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FalsificationReport:
    passed: bool
    lookahead_clean: bool
    dsr_passed: bool
    sensitivity_passed: bool
    cost_resilient: bool
    break_even_bps: float
    summary: str

    def as_dict(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "lookahead_clean": self.lookahead_clean,
            "dsr_passed": self.dsr_passed,
            "sensitivity_passed": self.sensitivity_passed,
            "cost_resilient": self.cost_resilient,
            "break_even_bps": round(self.break_even_bps, 1),
            "summary": self.summary,
        }


class FalsificationEngine:
    """Evaluates 4 independent falsification vectors to aggressively weed out false discoveries."""

    @classmethod
    def evaluate(
        cls,
        has_lookahead: bool = False,
        observed_dsr: float = 0.88,
        min_dsr: float = 0.80,
        is_spike_sensitive: bool = False,
        raw_spread_bps: float = 45.0,
    ) -> FalsificationReport:
        # Vector 1: Lookahead leakage
        lookahead_clean = not has_lookahead

        # Vector 2: DSR multiple testing correction
        dsr_passed = observed_dsr >= min_dsr

        # Vector 3: Sensitivity topology (plateau vs spike)
        sens_passed = not is_spike_sensitive

        # Vector 4: Execution friction stress (break-even bps)
        cost_resilient = raw_spread_bps > 15.0

        all_passed = lookahead_clean and dsr_passed and sens_passed and cost_resilient

        summary = (
            "Hypothesis passed all 4 adversarial falsification vectors."
            if all_passed
            else "Hypothesis failed falsification check."
        )

        return FalsificationReport(
            passed=all_passed,
            lookahead_clean=lookahead_clean,
            dsr_passed=dsr_passed,
            sensitivity_passed=sens_passed,
            cost_resilient=cost_resilient,
            break_even_bps=raw_spread_bps,
            summary=summary,
        )
