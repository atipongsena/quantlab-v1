"""Validation runner coordinating full falsification pipeline."""

from __future__ import annotations

from collections.abc import Sequence

from quantlab.validation.bootstrap import BootstrapRunner, BootstrapSpec
from quantlab.validation.candidate import FrozenCandidate
from quantlab.validation.gates import HardGateEvaluator
from quantlab.validation.multiple_testing import TrialDiagnostics
from quantlab.validation.result import ValidationResult
from quantlab.validation.robustness import RobustnessArtifact
from quantlab.validation.verdicts import VerdictEngine


class ValidationRunner:
    """Orchestrates comprehensive strategy validation and falsification."""

    @classmethod
    def run(
        cls,
        candidate: FrozenCandidate,
        returns_series: Sequence[float],
        robustness: RobustnessArtifact,
        trial_sharpes: Sequence[float] = (),
        lookahead_detected: bool = False,
        data_corrupt: bool = False,
        reproducibility_failed: bool = False,
        bootstrap_spec: BootstrapSpec | None = None,
    ) -> ValidationResult:
        # 1. Hard correctness gates
        hard_gates = HardGateEvaluator.evaluate_all(
            candidate=candidate,
            lookahead_detected=lookahead_detected,
            data_corrupt=data_corrupt,
            reproducibility_failed=reproducibility_failed,
        )

        # 2. Robustness evidence is supplied by the caller: it can only come from real
        # re-runs of the strategy, which the validation runner has no way to perform.

        # 3. Stationary block bootstrap
        bootstrap = BootstrapRunner.run(returns=returns_series, spec=bootstrap_spec)

        # 4. Multiple testing evidence. The trial ledger is what it is: with a single
        # recorded trial there is no measured spread of Sharpes to deflate against, and
        # the result leans on an assumed variance rather than on evidence.
        multiple_testing = TrialDiagnostics.evaluate(
            returns=returns_series,
            trial_sharpes=list(trial_sharpes),
        )

        # 5. Determine authoritative verdict
        verdict, reasons = VerdictEngine.determine_verdict(
            hard_gates=hard_gates,
            robustness=robustness,
            multiple_testing=multiple_testing,
        )

        return ValidationResult.create(
            candidate=candidate,
            verdict=verdict,
            reasons=tuple(reasons),
            hard_gates=hard_gates,
            robustness=robustness,
            bootstrap=bootstrap,
            multiple_testing=multiple_testing,
        )
