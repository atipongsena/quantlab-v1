from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from quantlab.domain.identity import (
    InstrumentId,
    _require_nonempty,
    require_date_only,
    require_nonnegative_decimal,
    require_positive_decimal,
    require_timezone_aware,
)


class BarPriceSemantic(StrEnum):
    """Price semantics a daily bar can carry.

    ``RAW`` is the tradable price: execution, fills, and cash accounting use it, and
    dividends are credited separately as cash. ``TOTAL_RETURN_ADJUSTED`` folds both
    splits and cash dividends back into the price series and is for return and factor
    research only. Mixing the two in one accounting path double-counts dividends.
    """

    RAW = "raw"
    TOTAL_RETURN_ADJUSTED = "adjusted"
    ADJUSTED = "adjusted"  # legacy alias for TOTAL_RETURN_ADJUSTED


@dataclass(frozen=True, slots=True)
class MarketBar:
    instrument_id: InstrumentId
    session: date
    observed_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    semantic: BarPriceSemantic
    source: str

    def __post_init__(self) -> None:
        if not isinstance(self.instrument_id, InstrumentId):
            raise TypeError("instrument_id must be InstrumentId")
        require_date_only(self.session, "session")
        require_timezone_aware(self.observed_at, "observed_at")
        require_positive_decimal(self.open, "open")
        require_positive_decimal(self.high, "high")
        require_positive_decimal(self.low, "low")
        require_positive_decimal(self.close, "close")
        require_nonnegative_decimal(self.volume, "volume")
        if self.high < max(self.open, self.low, self.close):
            raise ValueError("high must be at least open, low, and close")
        if self.low > min(self.open, self.high, self.close):
            raise ValueError("low must be no greater than open, high, and close")
        if not isinstance(self.semantic, BarPriceSemantic):
            raise TypeError("semantic must be BarPriceSemantic")
        _require_nonempty(self.source, "source")
