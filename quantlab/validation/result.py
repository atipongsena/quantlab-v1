"""Authoritative validation result and artifact contracts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from quantlab.validation.bootstrap import BootstrapDistribution
from quantlab.validation.candidate import FrozenCandidate
from quantlab.validation.gates import GateDecision
from quantlab.validation.multiple_testing import MultipleTestingEvidence
from quantlab.validation.robustness import RobustnessArtifact
from quantlab.validation.verdicts import ValidationVerdict


@dataclass(frozen=True, slots=True)
class ValidationResult:
    candidate: FrozenCandidate
    verdict: ValidationVerdict
    reasons: tuple[str, ...]
    hard_gates: tuple[GateDecision, ...]
    robustness: RobustnessArtifact
    bootstrap: BootstrapDistribution
    multiple_testing: MultipleTestingEvidence
    content_hash: str

    def as_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate.candidate_id,
            "strategy_id": self.candidate.strategy_id,
            "verdict": self.verdict.value,
            "reasons": list(self.reasons),
            "hard_gates": [g.as_dict() for g in self.hard_gates],
            "robustness": self.robustness.as_dict(),
            "bootstrap": self.bootstrap.as_dict(),
            "multiple_testing": {
                "n_trials": self.multiple_testing.n_trials,
                "observed_sharpe": self.multiple_testing.observed_sharpe,
                "deflated_sharpe_p_value": self.multiple_testing.deflated_sharpe_p_value,
                "is_statistically_significant": self.multiple_testing.is_statistically_significant,
                "is_multiple_testing_warned": self.multiple_testing.is_multiple_testing_warned,
            },
            "content_hash": self.content_hash,
        }

    @classmethod
    def create(
        cls,
        candidate: FrozenCandidate,
        verdict: ValidationVerdict,
        reasons: tuple[str, ...],
        hard_gates: tuple[GateDecision, ...],
        robustness: RobustnessArtifact,
        bootstrap: BootstrapDistribution,
        multiple_testing: MultipleTestingEvidence,
    ) -> ValidationResult:
        payload = {
            "candidate": candidate.as_dict(),
            "verdict": verdict.value,
            "reasons": list(reasons),
            "gates": [g.as_dict() for g in hard_gates],
            "robustness": robustness.as_dict(),
            "bootstrap": bootstrap.as_dict(),
        }
        encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
        chash = hashlib.sha256(encoded).hexdigest()

        return cls(
            candidate=candidate,
            verdict=verdict,
            reasons=reasons,
            hard_gates=hard_gates,
            robustness=robustness,
            bootstrap=bootstrap,
            multiple_testing=multiple_testing,
            content_hash=chash,
        )
