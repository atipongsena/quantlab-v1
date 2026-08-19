"""Tests for ValidationRunner end-to-end execution."""

from quantlab.validation.candidate import CandidateFreezer
from quantlab.validation.runner import ValidationRunner
from quantlab.validation.verdicts import ValidationVerdict
from tests.validation.factories import build_robustness


def test_validation_runner_full_pipeline() -> None:
    candidate = CandidateFreezer.freeze("test-strat", {"p": 1}, "git:abc")
    returns = [0.0008] * 252  # ~20% annualized return

    result = ValidationRunner.run(
        candidate=candidate,
        returns_series=returns,
        robustness=build_robustness(candidate),
    )

    assert result.candidate.candidate_id == candidate.candidate_id
    assert result.verdict in (ValidationVerdict.VALIDATED, ValidationVerdict.PAPER_CANDIDATE)
    assert result.content_hash != ""
    assert len(result.hard_gates) >= 4
