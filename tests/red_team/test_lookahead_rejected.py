"""Tests proving that lookahead leakage canary is correctly rejected."""

from quantlab.red_team.runner import RedTeamRunner
from quantlab.validation.gates import HardGateType
from quantlab.validation.verdicts import ValidationVerdict


def test_lookahead_canary_is_rejected() -> None:
    result = RedTeamRunner.run_lookahead_case()

    assert result.verdict == ValidationVerdict.REJECTED
    leakage_gate = next(
        g for g in result.hard_gates if g.gate_type == HardGateType.LOOKAHEAD_LEAKAGE
    )
    assert not leakage_gate.passed
    assert any("Lookahead leakage detected" in r for r in result.reasons)
