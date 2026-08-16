"""Validation critic engine and adversarial falsification protocol."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CriticVerdict:
    passed: bool
    score: float
    notes: str
    flaws_detected: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "score": round(self.score, 2),
            "notes": self.notes,
            "flaws_detected": list(self.flaws_detected),
        }


class ValidationCritic:
    """Adversarial critic challenging hypotheses, factor constructions, and overfitting."""

    @classmethod
    def evaluate_hypothesis(
        cls,
        premise: str,
        backtest_sharpe: float,
        sensitivity_fragile: bool = False,
        deflated_sharpe: float = 0.85,
    ) -> CriticVerdict:
        flaws: list[str] = []

        if backtest_sharpe < 0.8:
            flaws.append("Unsatisfactory raw backtest Sharpe ratio (<0.80)")

        if sensitivity_fragile:
            flaws.append("Fragile sensitivity topology: hyperparameter spike indicates overfit")

        if deflated_sharpe < 0.70:
            flaws.append("Deflated Sharpe ratio fails multiple testing significance (>0.70)")

        passed = len(flaws) == 0
        score = max(0.0, 1.0 - 0.3 * len(flaws))
        notes = (
            "Hypothesis satisfies adversarial falsification criteria."
            if passed
            else f"Falsification revealed {len(flaws)} critical vulnerabilities."
        )

        return CriticVerdict(
            passed=passed,
            score=score,
            notes=notes,
            flaws_detected=tuple(flaws),
        )
