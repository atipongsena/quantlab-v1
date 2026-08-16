"""Tests proving that random multi-trial mining triggers multiple testing warnings."""

from quantlab.validation.red_team import RedTeamRunner
from quantlab.validation.verdicts import ValidationVerdict


def test_random_mining_triggers_warning_and_research_only() -> None:
    result = RedTeamRunner.run_random_mining_case(n_trials=100, seed=42)

    assert result.verdict == ValidationVerdict.RESEARCH_ONLY
    assert result.multiple_testing.n_trials == 100
    assert result.multiple_testing.is_multiple_testing_warned
    assert any("Multiple testing warning" in r for r in result.reasons)
