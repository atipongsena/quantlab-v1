"""Registry for versioned factor definitions and implementations."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar

from quantlab.common.hashing import canonical_hash
from quantlab.factors.contracts import Factor, FactorDefinition


@dataclass(frozen=True, slots=True)
class FactorRegistration:
    definition: FactorDefinition
    factor: Factor
    implementation_hash: str
    version: str


class FactorRegistry:
    _global_registry: ClassVar[FactorRegistry | None] = None

    def __init__(self) -> None:
        self._factors: dict[str, FactorRegistration] = {}

    def register(
        self,
        factor: Factor,
        implementation_hash: str | None = None,
    ) -> FactorRegistration:
        definition = factor.definition
        factor_id = definition.factor_id

        # Compute combined version hash from definition hash and implementation hash
        imp_hash = implementation_hash or canonical_hash(
            {
                "formula": definition.formula,
                "version": definition.calculator_version,
                "inputs": list(definition.inputs),
            }
        )
        combined_payload = {
            "definition": definition.as_dict(),
            "implementation_hash": imp_hash,
        }
        version = canonical_hash(combined_payload)

        registration = FactorRegistration(
            definition=definition,
            factor=factor,
            implementation_hash=imp_hash,
            version=version,
        )
        self._factors[factor_id] = registration
        return registration

    def get(self, factor_id: str) -> Factor:
        if factor_id not in self._factors:
            raise KeyError(f"Factor not registered: {factor_id}")
        return self._factors[factor_id].factor

    def get_registration(self, factor_id: str) -> FactorRegistration:
        if factor_id not in self._factors:
            raise KeyError(f"Factor not registered: {factor_id}")
        return self._factors[factor_id]

    def list_definitions(self) -> Sequence[FactorDefinition]:
        return [reg.definition for reg in self._factors.values()]

    def list_factors(self) -> Sequence[FactorDefinition]:
        return self.list_definitions()

    def list_factor_ids(self) -> Sequence[str]:
        return list(self._factors.keys())

    def contains(self, factor_id: str) -> bool:
        return factor_id in self._factors

    @classmethod
    def global_instance(cls) -> FactorRegistry:
        if cls._global_registry is None:
            cls._global_registry = FactorRegistry()
        return cls._global_registry
