from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class InstrumentType(StrEnum):
    EQUITY = "equity"
    ETF = "etf"


class InstrumentStatus(StrEnum):
    ACTIVE = "active"
    DELISTED = "delisted"


@dataclass(frozen=True, slots=True)
class InstrumentId:
    value: UUID

    @classmethod
    def from_uuid(cls, value: UUID) -> InstrumentId:
        return cls(value)

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise TypeError("InstrumentId value must be a UUID")

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True, slots=True)
class Instrument:
    instrument_id: InstrumentId
    issuer_name: str
    security_name: str
    instrument_type: InstrumentType
    exchange: str
    currency: str
    active_from: date
    status: InstrumentStatus
    active_to: date | None = None

    def __post_init__(self) -> None:
        _require_type(self.instrument_id, InstrumentId, "instrument_id")
        _require_nonempty(self.issuer_name, "issuer_name")
        _require_nonempty(self.security_name, "security_name")
        _require_type(self.instrument_type, InstrumentType, "instrument_type")
        _require_nonempty(self.exchange, "exchange")
        _require_nonempty(self.currency, "currency")
        require_date_only(self.active_from, "active_from")
        _require_type(self.status, InstrumentStatus, "status")
        if self.active_to is not None:
            require_date_only(self.active_to, "active_to")
            if self.active_to < self.active_from:
                raise ValueError("active_to must be on or after active_from")

    def with_symbol_change(
        self, *, issuer_name: str, security_name: str, exchange: str
    ) -> Instrument:
        return replace(
            self,
            issuer_name=issuer_name,
            security_name=security_name,
            exchange=exchange,
        )


@dataclass(frozen=True, slots=True)
class SymbolHistory:
    instrument_id: InstrumentId
    symbol: str
    exchange: str
    valid_from: date
    source: str
    valid_to: date | None = None

    def __post_init__(self) -> None:
        _require_type(self.instrument_id, InstrumentId, "instrument_id")
        _require_nonempty(self.symbol, "symbol")
        _require_nonempty(self.exchange, "exchange")
        require_date_only(self.valid_from, "valid_from")
        _require_nonempty(self.source, "source")
        if self.valid_to is not None:
            require_date_only(self.valid_to, "valid_to")
            if self.valid_to < self.valid_from:
                raise ValueError("valid_to must be on or after valid_from")


def require_date_only(value: date, field_name: str) -> None:
    if not isinstance(value, date) or isinstance(value, datetime):
        raise TypeError(f"{field_name} must be a date without time")


def require_timezone_aware(value: datetime, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise TypeError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


def require_decimal(value: Decimal, field_name: str) -> None:
    if isinstance(value, float):
        raise TypeError(f"{field_name} must be Decimal; float input is rejected")
    if not isinstance(value, Decimal):
        raise TypeError(f"{field_name} must be Decimal")


def require_nonnegative_decimal(value: Decimal, field_name: str) -> None:
    require_decimal(value, field_name)
    if value < Decimal("0"):
        raise ValueError(f"{field_name} must be nonnegative")


def require_positive_decimal(value: Decimal, field_name: str) -> None:
    require_decimal(value, field_name)
    if value <= Decimal("0"):
        raise ValueError(f"{field_name} must be positive")


def _require_nonempty(value: str, field_name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value.strip():
        raise ValueError(f"{field_name} must be nonempty")


def _require_type(value: object, expected_type: type[object], field_name: str) -> None:
    if not isinstance(value, expected_type):
        raise TypeError(f"{field_name} must be {expected_type.__name__}")
