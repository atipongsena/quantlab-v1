"""Tests for Deflated Sharpe Ratio calculation."""

from quantlab.validation.deflated_sharpe import DeflatedSharpeCalculator


def test_deflated_sharpe_single_trial_high_confidence() -> None:
    # 1 trial with high Sharpe of 2.0 -> high DSR p-value (~1.0)
    p_val = DeflatedSharpeCalculator.calculate(
        observed_sharpe=2.0,
        n_trials=1,
        sample_length=252,
    )
    assert p_val > 0.95


def test_deflated_sharpe_multiple_trials_deflates_confidence() -> None:
    # After 1000 trials, a modest Sharpe of 1.0 is likely false positive
    p_val = DeflatedSharpeCalculator.calculate(
        observed_sharpe=1.0,
        n_trials=1000,
        variance_trials=0.25,
        sample_length=252,
    )
    assert p_val < 0.50
