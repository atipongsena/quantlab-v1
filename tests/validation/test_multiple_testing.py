"""Tests for multiple testing trial diagnostics."""

from quantlab.validation.multiple_testing import TrialDiagnostics


def test_trial_diagnostics_detects_multiple_testing_risk() -> None:
    # 100 trials with average Sharpe 0.8 and variance 0.30
    trial_sharpes = [0.8 + 0.1 * ((i % 10) - 5) for i in range(100)]
    evidence = TrialDiagnostics.evaluate(
        observed_sharpe=0.9,
        trial_sharpes=trial_sharpes,
        sample_length=252,
    )

    assert evidence.n_trials == 100
    assert evidence.is_multiple_testing_warned
