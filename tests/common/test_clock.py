from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from quantlab.common.clock import FrozenClock, require_utc


def test_frozen_clock_behavior_and_utc_enforcement() -> None:
    fixed = datetime(2024, 1, 31, 22, 0, tzinfo=UTC)
    clock = FrozenClock(fixed)

    assert clock.now() == fixed
    assert clock.now() is fixed

    with pytest.raises(ValueError, match="timezone-aware"):
        FrozenClock(datetime(2024, 1, 31, 22, 0))

    with pytest.raises(ValueError, match="UTC"):
        FrozenClock(datetime(2024, 1, 31, 22, 0, tzinfo=timezone(timedelta(hours=7))))


def test_require_utc_accepts_zero_offset_datetime() -> None:
    value = datetime(2024, 1, 31, 22, 0, tzinfo=UTC)

    assert require_utc(value) == value
