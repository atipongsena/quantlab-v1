"""Hard correctness gate evaluators."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from quantlab.validation.candidate import FrozenCandidate


class HardGateType(StrEnum):
    LOOKAHEAD_LEAKAGE = "lookahead_leakage"
    DATA_INTEGRITY = "data_integrity"
    AUTHORITY = "authority"
    REPRODUCIBILITY = "reproducibility"
    LOCKBOX_DISCIPLINE = "lockbox_discipline"


@dataclass(frozen=True, slots=True)
class GateDecision:
    gate_type: HardGateType
    passed: bool
    reason: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "gate_type": self.gate_type.value,
            "passed": self.passed,
            "reason": self.reason,
        }


class HardGateEvaluator:
    """Evaluates non-overrideable correctness and anti-leakage gates."""

    @classmethod
    def evaluate_authority(cls, candidate: FrozenCandidate | None) -> GateDecision:
        if candidate is None:
            return GateDecision(
                gate_type=HardGateType.AUTHORITY,
                passed=False,
                reason="Candidate is not frozen or missing lineage",
            )
        if not candidate.code_fingerprint or not candidate.config_hash:
            return GateDecision(
                gate_type=HardGateType.AUTHORITY,
                passed=False,
                reason="Candidate code fingerprint or config hash is empty",
            )
        return GateDecision(gate_type=HardGateType.AUTHORITY, passed=True)

    @classmethod
    def evaluate_leakage(cls, lookahead_detected: bool, details: str = "") -> GateDecision:
        if lookahead_detected:
            return GateDecision(
                gate_type=HardGateType.LOOKAHEAD_LEAKAGE,
                passed=False,
                reason=f"Lookahead leakage detected: {details}",
            )
        return GateDecision(gate_type=HardGateType.LOOKAHEAD_LEAKAGE, passed=True)

    @classmethod
    def evaluate_all(
        cls,
        candidate: FrozenCandidate | None,
        lookahead_detected: bool = False,
        data_corrupt: bool = False,
        reproducibility_failed: bool = False,
    ) -> tuple[GateDecision, ...]:
        decisions: list[GateDecision] = [cls.evaluate_authority(candidate)]

        if lookahead_detected:
            decisions.append(cls.evaluate_leakage(True, "forward information in features/signals"))
        else:
            decisions.append(cls.evaluate_leakage(False))

        if data_corrupt:
            decisions.append(
                GateDecision(
                    gate_type=HardGateType.DATA_INTEGRITY,
                    passed=False,
                    reason="Data integrity violation or corrupted bars",
                )
            )
        else:
            decisions.append(GateDecision(gate_type=HardGateType.DATA_INTEGRITY, passed=True))

        if reproducibility_failed:
            decisions.append(
                GateDecision(
                    gate_type=HardGateType.REPRODUCIBILITY,
                    passed=False,
                    reason="Backtest rerun yielded differing content hashes",
                )
            )
        else:
            decisions.append(GateDecision(gate_type=HardGateType.REPRODUCIBILITY, passed=True))

        return tuple(decisions)
