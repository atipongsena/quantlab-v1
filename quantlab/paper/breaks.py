"""Trade breaks and reconciliation severity classifications."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from quantlab.domain.identity import InstrumentId


class BreakSeverity(StrEnum):
    NONE = "NONE"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class BreakType(StrEnum):
    CASH_MISMATCH = "CASH_MISMATCH"
    POSITION_QUANTITY_MISMATCH = "POSITION_QUANTITY_MISMATCH"
    MISSING_POSITION = "MISSING_POSITION"
    UNEXPECTED_POSITION = "UNEXPECTED_POSITION"
    DIVIDEND_MISMATCH = "DIVIDEND_MISMATCH"


@dataclass(frozen=True, slots=True)
class TradeBreak:
    break_type: BreakType
    instrument_id: InstrumentId | None
    shadow_value: Decimal
    broker_value: Decimal
    difference: Decimal
    severity: BreakSeverity
    reason: str

    def as_dict(self) -> dict[str, object]:
        return {
            "break_type": self.break_type.value,
            "instrument_id": str(self.instrument_id.value) if self.instrument_id else None,
            "shadow_value": str(self.shadow_value),
            "broker_value": str(self.broker_value),
            "difference": str(self.difference),
            "severity": self.severity.value,
            "reason": self.reason,
        }
