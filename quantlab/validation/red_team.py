"""Red team runners executing flagship falsification demonstrations.

These three cases are deliberately rigged inputs, not measurements of any real
strategy. Each one constructs the evidence a specific failure mode would produce and
asserts that the gates reject it. Their value is negative: they show what the pipeline
refuses to certify (spec 7.13).
"""

from __future__ import annotations

import random
import uuid
from collections.abc import Mapping, Sequence
from decimal import Decimal

from quantlab.domain.identity import InstrumentId
from quantlab.validation.bootstrap import BootstrapRunner
from quantlab.validation.candidate import CandidateFreezer, FrozenCandidate
from quantlab.validation.gates import HardGateEvaluator
from quantlab.validation.multiple_testing import TrialDiagnostics
from quantlab.validation.result import ValidationResult
from quantlab.validation.robustness import RobustnessArtifact, RobustnessRunner
from quantlab.validation.runner import ValidationRunner
from quantlab.validation.sensitivity import SensitivityCell
from quantlab.validation.verdicts import VerdictEngine


def _scenario_robustness(
    candidate: FrozenCandidate,
    top_k_sharpes: Mapping[int, float],
    zero_cost_cagr: float,
    annual_turnover: float,
    baseline_sharpe: float,
    baseline_cagr: float,
    positions: int = 30,
) -> RobustnessArtifact:
    """Build the robustness evidence a scenario is defined to produce."""
    cells: Sequence[SensitivityCell] = [
        SensitivityCell(
            parameters={"top_k": top_k},
            sharpe_ratio=sharpe,
            cagr=zero_cost_cagr,
            max_drawdown=0.15,
        )
        for top_k, sharpe in sorted(top_k_sharpes.items())
    ]
    weight = Decimal("1") / Decimal(positions)
    weights = {InstrumentId(uuid.UUID(int=i + 1)): weight for i in range(positions)}

    return RobustnessRunner.run(
        candidate=candidate,
        top_k_cells=cells,
        zero_cost_cagr=zero_cost_cagr,
        annual_turnover=annual_turnover,
        terminal_weights=weights,
        sector_weights={
            "TECHNOLOGY": Decimal("0.30"),
            "HEALTHCARE": Decimal("0.25"),
            "FINANCIALS": Decimal("0.20"),
            "STAPLES": Decimal("0.25"),
        },
        ablation_results={"momentum_12_1": (baseline_sharpe * 0.85, baseline_cagr * 0.8)},
        baseline_sharpe=baseline_sharpe,
        baseline_cagr=baseline_cagr,
    )


class RedTeamRunner:
    """Orchestrates flagship red teaming attacks to demonstrate defense efficacy."""

    @classmethod
    def run_lookahead_case(cls) -> ValidationResult:
        """A strategy that peeks at tomorrow, with performance to match.

        The point is that the numbers are spectacular and the verdict is still REJECTED:
        a detected temporal leak is a hard failure that no downstream statistic can
        override (spec 7.11).
        """
        candidate = CandidateFreezer.freeze(
            strategy_id="canary-lookahead-v1",
            strategy_config={"factor_id": "forward_return_canary", "leakage_days": 1},
            code_fingerprint="canary:lookahead",
        )
        leaked_returns = [0.0050] * 252  # ~250% annualized, which is the tell

        return ValidationRunner.run(
            candidate=candidate,
            returns_series=leaked_returns,
            robustness=_scenario_robustness(
                candidate,
                top_k_sharpes={20: 7.8, 30: 8.0, 50: 7.6},
                zero_cost_cagr=2.5,
                annual_turnover=3.0,
                baseline_sharpe=8.0,
                baseline_cagr=2.5,
            ),
            lookahead_detected=True,  # Real detector catches the canary
        )

    @classmethod
    def run_random_mining_case(cls, n_trials: int = 100, seed: int = 42) -> ValidationResult:
        """Search 100 noise strategies and promote the best one.

        With enough trials some pure-noise strategy always posts an attractive Sharpe.
        The deflated statistic is what separates that from a finding.
        """
        candidate = CandidateFreezer.freeze(
            strategy_id="random-mining-v1",
            strategy_config={"n_trials": n_trials, "noise_seed": seed},
            code_fingerprint="mining:noise",
        )

        rng = random.Random(seed)
        trial_sharpes = [rng.gauss(0.0, 0.75) for _ in range(n_trials)]
        best_returns = [0.0005 + 0.01 * rng.gauss(0.0, 1.0) for _ in range(252)]

        return ValidationRunner.run(
            candidate=candidate,
            returns_series=best_returns,
            robustness=_scenario_robustness(
                candidate,
                top_k_sharpes={20: 0.4, 30: 1.2, 50: 0.3},  # a spike, not a plateau
                zero_cost_cagr=0.13,
                annual_turnover=4.0,
                baseline_sharpe=1.2,
                baseline_cagr=0.13,
            ),
            trial_sharpes=trial_sharpes,
        )

    @classmethod
    def run_cost_illusion_case(cls) -> ValidationResult:
        """A 3% gross edge traded 25 times a year, which costs more than it makes."""
        candidate = CandidateFreezer.freeze(
            strategy_id="high-turnover-illusion",
            strategy_config={"annual_turnover": 25.0, "gross_cagr": 0.03},
            code_fingerprint="stress:cost_illusion",
        )
        gross_returns = [0.00012] * 252

        hard_gates = HardGateEvaluator.evaluate_all(candidate)
        robustness = _scenario_robustness(
            candidate,
            top_k_sharpes={20: 1.05, 30: 1.10, 50: 1.02},
            zero_cost_cagr=0.03,
            annual_turnover=25.0,
            baseline_sharpe=1.10,
            baseline_cagr=0.03,
        )

        bootstrap = BootstrapRunner.run(gross_returns)
        mt = TrialDiagnostics.evaluate(returns=gross_returns, trial_sharpes=[])
        verdict, reasons = VerdictEngine.determine_verdict(hard_gates, robustness, mt)

        return ValidationResult.create(
            candidate=candidate,
            verdict=verdict,
            reasons=tuple(reasons),
            hard_gates=hard_gates,
            robustness=robustness,
            bootstrap=bootstrap,
            multiple_testing=mt,
        )

    @classmethod
    def run_all(cls) -> list[ValidationResult]:
        return [
            cls.run_lookahead_case(),
            cls.run_random_mining_case(),
            cls.run_cost_illusion_case(),
        ]
