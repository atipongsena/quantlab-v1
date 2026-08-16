"""Tests proving that frictional cost illusion is caught and downgraded."""

from quantlab.red_team.runner import RedTeamRunner
from quantlab.validation.verdicts import ValidationVerdict


def test_cost_illusion_downgraded_to_research_only() -> None:
    result = RedTeamRunner.run_cost_illusion_case()

    assert result.verdict == ValidationVerdict.RESEARCH_ONLY
    assert result.robustness.cost_stress.is_cost_fragile
    assert result.robustness.cost_stress.break_even_cost_bps < 10.0
    assert any("Cost fragile" in r for r in result.reasons)
