"""Tests for FactorRegistry."""

import uuid

from quantlab.domain.identity import InstrumentId
from quantlab.factors.contracts import (
    Factor,
    FactorCategory,
    FactorContext,
    FactorDefinition,
    FactorSnapshot,
    FactorValue,
)
from quantlab.factors.registry import FactorRegistry


class DummyMomentumFactor(Factor):
    def __init__(self, factor_id: str = "mom_dummy", version: str = "v1") -> None:
        self._def = FactorDefinition(
            factor_id=factor_id,
            name="Dummy Momentum",
            category=FactorCategory.MOMENTUM.value,
            description="Dummy momentum calculation",
            formula="close[-1] / close[-20] - 1",
            direction=1,
            inputs=("prices",),
            lookback_sessions=20,
            availability_lag_sessions=0,
            missingness_policy="insufficient_history",
            price_semantic="total_return",
            calculator_version=version,
        )

    @property
    def definition(self) -> FactorDefinition:
        return self._def

    def compute(self, context: FactorContext) -> FactorSnapshot:
        inst = InstrumentId(uuid.uuid4())
        values = {inst: FactorValue(instrument_id=inst, value=0.05)}
        return FactorSnapshot.create(
            factor_id=self._def.factor_id,
            version=self._def.calculator_version,
            session=context.session,
            as_of=context.as_of,
            values=values,
        )


def test_factor_registry_crud_and_versioning() -> None:
    registry = FactorRegistry()
    factor_v1 = DummyMomentumFactor(version="v1")
    reg_v1 = registry.register(factor_v1)

    assert registry.contains("mom_dummy")
    assert registry.get("mom_dummy") is factor_v1
    assert "mom_dummy" in registry.list_factor_ids()
    assert len(registry.list_definitions()) == 1

    # Same definition produces same version
    reg_v1_again = registry.register(factor_v1)
    assert reg_v1.version == reg_v1_again.version

    # Altering calculator version updates version hash
    factor_v2 = DummyMomentumFactor(version="v2")
    reg_v2 = registry.register(factor_v2)
    assert reg_v1.version != reg_v2.version
