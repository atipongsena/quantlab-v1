"""Multiple testing trial diagnostics and trial count tracking."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from quantlab.validation.deflated_sharpe import DeflatedSharpeCalculator


@dataclass(frozen=True, slots=True)
class MultipleTestingEvidence:
    n_trials: int
    variance_sharpes: float
    observed_sharpe: float
    deflated_sharpe_p_value: float
    is_statistically_significant: bool
    is_multiple_testing_warned: bool


class TrialDiagnostics:
    """Evaluates multiple testing evidence across a set of historical research trials."""

    @classmethod
    def evaluate(
        cls,
        observed_sharpe: float,
        trial_sharpes: Sequence[float],
        sample_length: int = 252,
    ) -> MultipleTestingEvidence:
        n = len(trial_sharpes)
        if n < 2:
            var_sharpe = 0.25
        else:
            mean_s = sum(trial_sharpes) / n
            var_sharpe = sum((s - mean_s) ** 2 for s in trial_sharpes) / (n - 1)
            if var_sharpe < 1e-4:
                var_sharpe = 0.25

        dsr_p = DeflatedSharpeCalculator.calculate(
            observed_sharpe=observed_sharpe,
            n_trials=max(1, n),
            variance_trials=var_sharpe,
            sample_length=sample_length,
        )

        is_sig = dsr_p >= 0.95
        is_warned = n >= 50 or (n > 5 and dsr_p < 0.95)

        return MultipleTestingEvidence(
            n_trials=n,
            variance_sharpes=round(var_sharpe, 4),
            observed_sharpe=round(observed_sharpe, 4),
            deflated_sharpe_p_value=round(dsr_p, 4),
            is_statistically_significant=is_sig,
            is_multiple_testing_warned=is_warned,
        )
