"""Tests for ValidationCritic adversarial evaluation."""

from quantlab.agents.critic import ValidationCritic


def test_validation_critic_passes_robust_hypothesis() -> None:
    verdict = ValidationCritic.evaluate_hypothesis(
        premise="Momentum + Quality",
        backtest_sharpe=1.35,
        sensitivity_fragile=False,
        deflated_sharpe=0.88,
    )
    assert verdict.passed
    assert verdict.score == 1.0
    assert len(verdict.flaws_detected) == 0


def test_validation_critic_rejects_fragile_hypothesis() -> None:
    verdict = ValidationCritic.evaluate_hypothesis(
        premise="Spike parameter",
        backtest_sharpe=1.20,
        sensitivity_fragile=True,
        deflated_sharpe=0.60,
    )
    assert not verdict.passed
    assert verdict.score < 0.8
    assert len(verdict.flaws_detected) == 2
