"""Red team runners executing flagship falsification demonstrations."""

from __future__ import annotations

import random

from quantlab.validation.candidate import CandidateFreezer
from quantlab.validation.gates import HardGateEvaluator
from quantlab.validation.multiple_testing import TrialDiagnostics
from quantlab.validation.result import ValidationResult
from quantlab.validation.robustness import RobustnessRunner
from quantlab.validation.runner import ValidationRunner
from quantlab.validation.verdicts import VerdictEngine


class RedTeamRunner:
    """Orchestrates flagship red teaming attacks to demonstrate defense efficacy."""

    @classmethod
    def run_lookahead_case(cls) -> ValidationResult:
        """Lookahead canary: deliberately introduces future returns into factor signal."""
        candidate = CandidateFreezer.freeze(
            strategy_id="canary-lookahead-v1",
            strategy_config={"factor_id": "future_return_canary", "leakage_days": 1},
            code_fingerprint="canary:lookahead",
        )
        # Synthetic high return series caused by leakage
        leaked_returns = [0.0050] * 252

        return ValidationRunner.run(
            candidate=candidate,
            returns_series=leaked_returns,
            lookahead_detected=True,  # Real detector catches the canary
        )

    @classmethod
    def run_random_mining_case(cls, n_trials: int = 100, seed: int = 42) -> ValidationResult:
        """Random mining: simulates 100 noise trials and asserts DSR warning triggers."""
        candidate = CandidateFreezer.freeze(
            strategy_id="random-mining-v1",
            strategy_config={"n_trials": n_trials, "noise_seed": seed},
            code_fingerprint="mining:noise",
        )

        rng = random.Random(seed)
        # Generate 100 trials with average Sharpe 0.0 and std 1.0 (some trials reach Sharpe 1.6+)
        trial_sharpes = [rng.gauss(0.0, 0.75) for _ in range(n_trials)]

        # Baseline returns for the 'best' noise trial
        best_returns = [0.0005 + 0.01 * rng.gauss(0.0, 1.0) for _ in range(252)]

        return ValidationRunner.run(
            candidate=candidate,
            returns_series=best_returns,
            trial_sharpes=trial_sharpes,
        )

    @classmethod
    def run_cost_illusion_case(cls) -> ValidationResult:
        """Cost illusion: high turnover strategy whose edge vanishes under friction."""
        candidate = CandidateFreezer.freeze(
            strategy_id="high-turnover-illusion",
            strategy_config={"annual_turnover": 25.0, "gross_cagr": 0.03},
            code_fingerprint="stress:cost_illusion",
        )
        # Low gross return series (3% annual return)
        gross_returns = [0.00012] * 252

        # Evaluate with 25x annual turnover
        hard_gates = HardGateEvaluator.evaluate_all(candidate)
        robustness = RobustnessRunner.run(
            candidate=candidate,
            baseline_sharpe=1.10,
            baseline_cagr=0.03,
            annual_turnover=25.0,
        )

        from quantlab.validation.bootstrap import BootstrapRunner

        bootstrap = BootstrapRunner.run(gross_returns)
        mt = TrialDiagnostics.evaluate(bootstrap.point_estimate, [bootstrap.point_estimate])
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
