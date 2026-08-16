"""Tests for HistoricalClock session event generation."""

from datetime import date

from quantlab.backtest.clock import HistoricalClock
from quantlab.backtest.events import (
    MarketCloseEvent,
    MarketOpenEvent,
    RebalanceDecisionEvent,
)


def test_historical_clock_events_stream() -> None:
    sessions = (date(2026, 1, 2), date(2026, 1, 5))
    clock = HistoricalClock(
        sessions=sessions,
        rebalance_sessions=(date(2026, 1, 5),),
        strategy_id="strat-01",
    )

    events = list(clock.events())
    assert len(events) == 5

    # Day 1: Open, Close
    assert isinstance(events[0], MarketOpenEvent)
    assert events[0].session == date(2026, 1, 2)
    assert isinstance(events[1], MarketCloseEvent)
    assert events[1].session == date(2026, 1, 2)

    # Day 2: Open, Close, RebalanceDecision
    assert isinstance(events[2], MarketOpenEvent)
    assert events[2].session == date(2026, 1, 5)
    assert isinstance(events[3], MarketCloseEvent)
    assert events[3].session == date(2026, 1, 5)
    assert isinstance(events[4], RebalanceDecisionEvent)
    assert events[4].session == date(2026, 1, 5)
    assert events[4].strategy_id == "strat-01"
