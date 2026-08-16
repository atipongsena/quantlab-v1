from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from quantlab.domain.identity import (
    InstrumentId,
    _require_nonempty,
    require_decimal,
    require_timezone_aware,
)


class SignalDirection(StrEnum):
    LONG = "long"
    FLAT = "flat"


@dataclass(frozen=True, slots=True)
class Signal:
    instrument_id: InstrumentId
    decision_time: datetime
    direction: SignalDirection
    score: Decimal
    model_id: str
    source_dataset_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.instrument_id, InstrumentId):
            raise TypeError("instrument_id must be InstrumentId")
        require_timezone_aware(self.decision_time, "decision_time")
        if not isinstance(self.direction, SignalDirection):
            raise TypeError("direction must be SignalDirection")
        require_decimal(self.score, "score")
        _require_nonempty(self.model_id, "model_id")
        _require_nonempty(self.source_dataset_id, "source_dataset_id")


@dataclass(frozen=True, slots=True)
class AlphaSnapshot:
    snapshot_id: str
    decision_time: datetime
    signals: tuple[Signal, ...]
    source_dataset_id: str

    def __post_init__(self) -> None:
        _require_nonempty(self.snapshot_id, "snapshot_id")
        require_timezone_aware(self.decision_time, "decision_time")
        if not isinstance(self.signals, tuple):
            raise TypeError("signals must be a tuple")
        if not self.signals:
            raise ValueError("signals must not be empty")
        for signal in self.signals:
            if not isinstance(signal, Signal):
                raise TypeError("signals must contain Signal values")
            if signal.decision_time != self.decision_time:
                raise ValueError("signal decision_time must match snapshot decision_time")
        _require_nonempty(self.source_dataset_id, "source_dataset_id")
