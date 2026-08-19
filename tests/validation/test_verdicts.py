"""Tests for validation verdict determination."""

from quantlab.validation.candidate import CandidateFreezer
from quantlab.validation.gates import HardGateEvaluator
from quantlab.validation.multiple_testing import MultipleTestingEvidence
from quantlab.validation.verdicts import ValidationVerdict, VerdictEngine
from tests.validation.factories import build_robustness


def test_verdict_engine_clean_candidate_paper_candidate() -> None:
    candidate = CandidateFreezer.freeze("top30", {"top_k": 30}, "git:clean")
    hard_gates = HardGateEvaluator.evaluate_all(candidate)
    robustness = build_robustness(candidate)
    mt = MultipleTestingEvidence(
        n_trials=5,
        variance_sharpes=0.1,
        observed_sharpe=1.25,
        observed_sharpe_per_period=0.0787,
        skewness=-0.1,
        excess_kurtosis=1.2,
        expected_max_sharpe=0.05,
        deflated_sharpe_p_value=0.98,
        is_statistically_significant=True,
        is_multiple_testing_warned=False,
    )

    verdict, reasons = VerdictEngine.determine_verdict(hard_gates, robustness, mt)
    assert verdict == ValidationVerdict.PAPER_CANDIDATE


def test_verdict_engine_hard_gate_failure_rejected() -> None:
    candidate = CandidateFreezer.freeze("top30", {"top_k": 30}, "git:clean")
    hard_gates = HardGateEvaluator.evaluate_all(candidate, lookahead_detected=True)
    robustness = build_robustness(candidate)
    mt = MultipleTestingEvidence(
        n_trials=1,
        variance_sharpes=0.1,
        observed_sharpe=1.25,
        observed_sharpe_per_period=0.0787,
        skewness=-0.1,
        excess_kurtosis=1.2,
        expected_max_sharpe=0.0,
        deflated_sharpe_p_value=0.99,
        is_statistically_significant=True,
        is_multiple_testing_warned=False,
    )

    verdict, reasons = VerdictEngine.determine_verdict(hard_gates, robustness, mt)
    assert verdict == ValidationVerdict.REJECTED
