"""Contracts and domain representations for QuantLab factors."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from typing import Protocol, runtime_checkable

from quantlab.common.hashing import canonical_hash
from quantlab.data.pit_facade import PointInTimeData
from quantlab.domain.identity import InstrumentId


class FactorCategory(StrEnum):
    MOMENTUM = "momentum"
    VALUE = "value"
    QUALITY = "quality"
    GROWTH = "growth"
    RISK = "risk"
    COMPOSITE = "composite"


class MissingReason(StrEnum):
    INSUFFICIENT_HISTORY = "insufficient_history"
    MISSING_FUNDAMENTAL = "missing_fundamental"
    INVALID_DENOMINATOR = "invalid_denominator"
    STALE_DATA = "stale_data"
    OUT_OF_RANGE = "out_of_range"
    NOT_IN_UNIVERSE = "not_in_universe"


@dataclass(frozen=True, slots=True)
class FactorDefinition:
    factor_id: str
    name: str
    category: str
    description: str
    formula: str
    direction: int
    inputs: tuple[str, ...]
    lookback_sessions: int
    availability_lag_sessions: int
    missingness_policy: str
    price_semantic: str
    calculator_version: str

    def as_dict(self) -> dict[str, object]:
        return {
            "factor_id": self.factor_id,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "formula": self.formula,
            "direction": self.direction,
            "inputs": list(self.inputs),
            "lookback_sessions": self.lookback_sessions,
            "availability_lag_sessions": self.availability_lag_sessions,
            "missingness_policy": self.missingness_policy,
            "price_semantic": self.price_semantic,
            "calculator_version": self.calculator_version,
        }

    @property
    def definition_hash(self) -> str:
        return canonical_hash(self.as_dict())


@dataclass(frozen=True, slots=True)
class FactorValue:
    instrument_id: InstrumentId
    value: float | None
    missing_reason: MissingReason | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        return self.value is not None and self.missing_reason is None

    def as_dict(self) -> dict[str, object]:
        return {
            "instrument_id": str(self.instrument_id.value),
            "value": self.value,
            "missing_reason": self.missing_reason.value if self.missing_reason else None,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class FactorContext:
    dataset_id: str
    session: date
    as_of: datetime
    pit_data: PointInTimeData
    universe: Sequence[InstrumentId]
    parameters: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FactorSnapshot:
    factor_id: str
    version: str
    session: date
    as_of: datetime
    values: Mapping[InstrumentId, FactorValue]
    content_hash: str
    metadata: Mapping[str, object] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        factor_id: str,
        version: str,
        session: date,
        as_of: datetime,
        values: Mapping[InstrumentId, FactorValue],
        metadata: Mapping[str, object] | None = None,
    ) -> FactorSnapshot:
        # Build canonical payload sorted by instrument_id value
        sorted_items = sorted(
            values.items(),
            key=lambda item: str(item[0].value),
        )
        payload = {
            "factor_id": factor_id,
            "version": version,
            "session": session.isoformat(),
            "as_of": as_of.isoformat(),
            "values": [val.as_dict() for _, val in sorted_items],
            "metadata": dict(metadata or {}),
        }
        digest = canonical_hash(payload)
        return cls(
            factor_id=factor_id,
            version=version,
            session=session,
            as_of=as_of,
            values=values,
            content_hash=digest,
            metadata=metadata or {},
        )

    def get_score(self, instrument_id: InstrumentId) -> float | None:
        val = self.values.get(instrument_id)
        if val is None or not val.is_valid:
            return None
        return val.value

    def valid_scores(self) -> dict[InstrumentId, float]:
        return {
            inst_id: val.value
            for inst_id, val in self.values.items()
            if val.value is not None and val.missing_reason is None
        }

    def as_dict(self) -> dict[str, object]:
        return {
            "factor_id": self.factor_id,
            "version": self.version,
            "session": self.session.isoformat(),
            "as_of": self.as_of.isoformat(),
            "content_hash": self.content_hash,
            "values": {str(inst.value): val.as_dict() for inst, val in self.values.items()},
            "metadata": dict(self.metadata),
        }


@runtime_checkable
class Factor(Protocol):
    @property
    def definition(self) -> FactorDefinition: ...

    def compute(self, context: FactorContext) -> FactorSnapshot: ...
