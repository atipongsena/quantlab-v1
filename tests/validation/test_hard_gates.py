"""Tests for hard correctness gates."""

from quantlab.validation.candidate import CandidateFreezer
from quantlab.validation.gates import HardGateEvaluator, HardGateType


def test_hard_gates_pass_on_clean_candidate() -> None:
    candidate = CandidateFreezer.freeze("strat-1", {"param": 1}, "git:sha1")
    decisions = HardGateEvaluator.evaluate_all(
        candidate=candidate,
        lookahead_detected=False,
        data_corrupt=False,
        reproducibility_failed=False,
    )

    assert all(d.passed for d in decisions)


def test_hard_gates_fail_on_lookahead_leakage() -> None:
    candidate = CandidateFreezer.freeze("strat-1", {"param": 1}, "git:sha1")
    decisions = HardGateEvaluator.evaluate_all(
        candidate=candidate,
        lookahead_detected=True,
    )

    leakage_dec = next(d for d in decisions if d.gate_type == HardGateType.LOOKAHEAD_LEAKAGE)
    assert not leakage_dec.passed
    assert "Lookahead leakage detected" in (leakage_dec.reason or "")
