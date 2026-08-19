"""Multiple testing trial diagnostics and trial count tracking."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from quantlab.validation.deflated_sharpe import DeflatedSharpeCalculator

TRADING_DAYS_PER_YEAR = 252.0

# Spread of Sharpe ratios across trials, used when the trial ledger is too thin to
# estimate one. 0.5 in Sharpe terms is the conventional stand-in from the Deflated
# Sharpe literature; it is a stated assumption, not a measurement.
DEFAULT_TRIAL_VARIANCE = 0.25


@dataclass(frozen=True, slots=True)
class MultipleTestingEvidence:
    n_trials: int
    variance_sharpes: float
    observed_sharpe: float
    observed_sharpe_per_period: float
    skewness: float
    excess_kurtosis: float
    expected_max_sharpe: float
    deflated_sharpe_p_value: float
    is_statistically_significant: bool
    is_multiple_testing_warned: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "n_trials": self.n_trials,
            "variance_sharpes": self.variance_sharpes,
            "observed_sharpe": self.observed_sharpe,
            "observed_sharpe_per_period": self.observed_sharpe_per_period,
            "skewness": self.skewness,
            "excess_kurtosis": self.excess_kurtosis,
            "expected_max_sharpe": self.expected_max_sharpe,
            "deflated_sharpe_p_value": self.deflated_sharpe_p_value,
            "is_statistically_significant": self.is_statistically_significant,
            "is_multiple_testing_warned": self.is_multiple_testing_warned,
        }


def _moments(returns: Sequence[float]) -> tuple[float, float, float, float]:
    """Return mean, standard deviation, skewness, and kurtosis of a return series."""
    n = len(returns)
    if n < 4:
        return 0.0, 0.0, 0.0, 3.0

    mean = sum(returns) / n
    variance = sum((r - mean) ** 2 for r in returns) / (n - 1)
    sd = math.sqrt(variance)
    if sd < 1e-12:
        return mean, 0.0, 0.0, 3.0

    skewness = sum(((r - mean) / sd) ** 3 for r in returns) / n
    kurtosis = sum(((r - mean) / sd) ** 4 for r in returns) / n
    return mean, sd, skewness, kurtosis


class TrialDiagnostics:
    """Evaluates multiple testing evidence across a set of historical research trials."""

    @classmethod
    def evaluate(
        cls,
        returns: Sequence[float],
        trial_sharpes: Sequence[float] = (),
        periods_per_year: float = TRADING_DAYS_PER_YEAR,
    ) -> MultipleTestingEvidence:
        """Deflate the observed Sharpe for trial count and for non-normal returns.

        The Deflated Sharpe standard error is defined on the *per-period* Sharpe with
        the sample length measured in those same periods. Feeding it an annualized
        Sharpe alongside a daily sample count inflates the statistic by roughly the
        annualization factor and turns almost any strategy significant.

        Skewness and kurtosis are estimated from the realized series rather than assumed
        normal. Correcting for fat tails and negative skew is the entire reason the
        deflated statistic exists; a strategy that earns steadily and then gaps down is
        exactly the case a normal assumption would wave through.
        """
        n = len(trial_sharpes)
        if n < 2:
            var_sharpe = DEFAULT_TRIAL_VARIANCE
        else:
            mean_s = sum(trial_sharpes) / n
            var_sharpe = sum((s - mean_s) ** 2 for s in trial_sharpes) / (n - 1)
            if var_sharpe < 1e-4:
                var_sharpe = DEFAULT_TRIAL_VARIANCE

        mean, sd, skewness, kurtosis = _moments(returns)
        sharpe_per_period = (mean / sd) if sd > 1e-12 else 0.0
        annualized_sharpe = sharpe_per_period * math.sqrt(periods_per_year)

        n_trials = max(1, n)
        dsr_p = DeflatedSharpeCalculator.calculate(
            observed_sharpe=sharpe_per_period,
            n_trials=n_trials,
            variance_trials=var_sharpe,
            skewness=skewness,
            kurtosis=kurtosis,
            sample_length=len(returns),
        )
        expected_max = DeflatedSharpeCalculator.expected_max_sharpe(n_trials, var_sharpe)

        is_sig = dsr_p >= 0.95
        is_warned = n >= 50 or (n > 5 and dsr_p < 0.95)

        return MultipleTestingEvidence(
            n_trials=n,
            variance_sharpes=round(var_sharpe, 4),
            observed_sharpe=round(annualized_sharpe, 4),
            observed_sharpe_per_period=round(sharpe_per_period, 6),
            skewness=round(skewness, 4),
            excess_kurtosis=round(kurtosis - 3.0, 4),
            expected_max_sharpe=round(expected_max, 6),
            deflated_sharpe_p_value=round(dsr_p, 4),
            is_statistically_significant=is_sig,
            is_multiple_testing_warned=is_warned,
        )
