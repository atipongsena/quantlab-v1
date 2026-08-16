from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from quantlab.domain.identity import (
    InstrumentId,
    _require_nonempty,
    require_date_only,
    require_positive_decimal,
    require_timezone_aware,
)


class CorporateActionType(StrEnum):
    SPLIT = "split"
    DIVIDEND = "dividend"
    SYMBOL_CHANGE = "symbol_change"
    MERGER = "merger"
    SPINOFF = "spinoff"


@dataclass(frozen=True, slots=True)
class CorporateAction:
    instrument_id: InstrumentId
    action_type: CorporateActionType
    effective_at: date
    announced_at: datetime
    available_at: datetime
    ratio: Decimal | None
    cash_amount: Decimal | None
    source: str

    def __post_init__(self) -> None:
        if not isinstance(self.instrument_id, InstrumentId):
            raise TypeError("instrument_id must be InstrumentId")
        if not isinstance(self.action_type, CorporateActionType):
            raise TypeError("action_type must be CorporateActionType")
        require_date_only(self.effective_at, "effective_at")
        require_timezone_aware(self.announced_at, "announced_at")
        require_timezone_aware(self.available_at, "available_at")
        if self.ratio is not None:
            require_positive_decimal(self.ratio, "ratio")
        if self.cash_amount is not None:
            require_positive_decimal(self.cash_amount, "cash_amount")
        if self.available_at < self.announced_at:
            raise ValueError("available_at must be on or after announced_at")
        _require_nonempty(self.source, "source")
