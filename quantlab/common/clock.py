from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

type TimePoint = datetime


class Clock(Protocol):
    def now(self) -> TimePoint: ...


@dataclass(frozen=True, slots=True)
class FrozenClock:
    fixed_time: TimePoint

    def __post_init__(self) -> None:
        require_utc(self.fixed_time)

    def now(self) -> TimePoint:
        return self.fixed_time


class SystemClock:
    def now(self) -> TimePoint:
        return datetime.now(UTC)


def require_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timepoint must be timezone-aware")
    if value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("timepoint must be UTC")
    return value
