from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from quantlab.domain.identity import (
    InstrumentId,
    _require_nonempty,
    require_decimal,
    require_nonnegative_decimal,
    require_timezone_aware,
)


@dataclass(frozen=True, slots=True)
class TargetPosition:
    instrument_id: InstrumentId
    target_weight: Decimal
    target_quantity: Decimal | None

    def __post_init__(self) -> None:
        if not isinstance(self.instrument_id, InstrumentId):
            raise TypeError("instrument_id must be InstrumentId")
        require_nonnegative_decimal(self.target_weight, "target_weight")
        if self.target_quantity is not None:
            require_nonnegative_decimal(self.target_quantity, "target_quantity")


@dataclass(frozen=True, slots=True)
class TargetPortfolio:
    portfolio_id: str
    decision_time: datetime
    positions: tuple[TargetPosition, ...]
    source_alpha_snapshot_id: str

    def __post_init__(self) -> None:
        _require_nonempty(self.portfolio_id, "portfolio_id")
        require_timezone_aware(self.decision_time, "decision_time")
        _require_positions_tuple(self.positions, TargetPosition, "positions")
        _require_unique_instruments(position.instrument_id for position in self.positions)
        _require_nonempty(self.source_alpha_snapshot_id, "source_alpha_snapshot_id")


@dataclass(frozen=True, slots=True)
class Position:
    instrument_id: InstrumentId
    quantity: Decimal
    cost_basis: Decimal
    market_value: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.instrument_id, InstrumentId):
            raise TypeError("instrument_id must be InstrumentId")
        require_decimal(self.quantity, "quantity")
        require_decimal(self.cost_basis, "cost_basis")
        require_decimal(self.market_value, "market_value")


@dataclass(frozen=True, slots=True)
class PortfolioSnapshot:
    portfolio_id: str
    as_of: datetime
    cash: Decimal
    positions: tuple[Position, ...]

    def __post_init__(self) -> None:
        _require_nonempty(self.portfolio_id, "portfolio_id")
        require_timezone_aware(self.as_of, "as_of")
        require_decimal(self.cash, "cash")
        _require_positions_tuple(self.positions, Position, "positions")
        _require_unique_instruments(position.instrument_id for position in self.positions)


def _require_positions_tuple(
    values: tuple[TargetPosition, ...] | tuple[Position, ...],
    item_type: type[TargetPosition] | type[Position],
    field_name: str,
) -> None:
    if not isinstance(values, tuple):
        raise TypeError(f"{field_name} must be a tuple")
    for value in values:
        if not isinstance(value, item_type):
            raise TypeError(f"{field_name} must contain {item_type.__name__} values")


def _require_unique_instruments(instrument_ids: Iterable[InstrumentId]) -> None:
    seen: set[InstrumentId] = set()
    for instrument_id in instrument_ids:
        if not isinstance(instrument_id, InstrumentId):
            raise TypeError("instrument ids must be InstrumentId values")
        if instrument_id in seen:
            raise ValueError("positions must be unique by instrument_id")
        seen.add(instrument_id)
