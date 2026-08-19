"""Tests for multiple testing trial diagnostics."""

import math

from quantlab.validation.multiple_testing import TrialDiagnostics


def _returns(mean: float, sd: float, n: int = 1008) -> list[float]:
    """Deterministic series with a target mean and dispersion."""
    return [mean + sd * math.sin(i * 0.7) for i in range(n)]


def test_trial_diagnostics_detects_multiple_testing_risk() -> None:
    # 100 recorded trials: the best of many is expected to look good by chance alone.
    trial_sharpes = [0.8 + 0.1 * ((i % 10) - 5) for i in range(100)]
    evidence = TrialDiagnostics.evaluate(
        returns=_returns(0.0006, 0.01),
        trial_sharpes=trial_sharpes,
    )

    assert evidence.n_trials == 100
    assert evidence.is_multiple_testing_warned
    assert evidence.expected_max_sharpe > 0.0


def test_deflated_sharpe_uses_per_period_units() -> None:
    """The deflated statistic must be computed on the per-period Sharpe.

    Feeding it an annualized Sharpe against a daily sample count inflates the ratio by
    roughly sqrt(252) and makes almost anything significant.
    """
    evidence = TrialDiagnostics.evaluate(returns=_returns(0.0006, 0.01), trial_sharpes=[1.0])

    assert evidence.observed_sharpe_per_period < 0.2
    assert evidence.observed_sharpe == round(
        evidence.observed_sharpe_per_period * math.sqrt(252.0), 4
    )


def test_non_normal_returns_are_penalised() -> None:
    """A negatively skewed, fat-tailed series must deflate harder than a clean one."""
    clean = TrialDiagnostics.evaluate(returns=_returns(0.0008, 0.01), trial_sharpes=[1.0])

    crashy = list(_returns(0.0008, 0.01))
    crashy[100] = -0.18
    crashy[400] = -0.15
    shocked = TrialDiagnostics.evaluate(returns=crashy, trial_sharpes=[1.0])

    assert shocked.skewness < clean.skewness
    assert shocked.deflated_sharpe_p_value <= clean.deflated_sharpe_p_value
