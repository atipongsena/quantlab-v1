"""Tests for 4-vector adversarial falsification engine."""

from quantlab.research.falsification import FalsificationEngine


def test_falsification_engine_clean_hypothesis() -> None:
    rep = FalsificationEngine.evaluate(
        has_lookahead=False,
        observed_dsr=0.85,
        min_dsr=0.80,
        is_spike_sensitive=False,
        raw_spread_bps=30.0,
    )
    assert rep.passed
    assert rep.lookahead_clean
    assert rep.dsr_passed
    assert rep.sensitivity_passed
    assert rep.cost_resilient


def test_falsification_engine_catches_overfit() -> None:
    rep = FalsificationEngine.evaluate(
        has_lookahead=False,
        observed_dsr=0.65,  # below 0.80 threshold
        min_dsr=0.80,
        is_spike_sensitive=True,  # fragile spike
        raw_spread_bps=5.0,  # below 15 bps cost floor
    )
    assert not rep.passed
    assert not rep.dsr_passed
    assert not rep.sensitivity_passed
    assert not rep.cost_resilient
