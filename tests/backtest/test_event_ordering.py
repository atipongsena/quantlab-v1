"""Tests for EventSequencer deterministic ordering."""

from datetime import UTC, date, datetime

from quantlab.backtest.events import (
    EventPriority,
    MarketCloseEvent,
    MarketOpenEvent,
    RebalanceDecisionEvent,
)
from quantlab.backtest.ordering import EventSequencer


def test_event_sequencer_orders_by_time_and_priority() -> None:
    session = date(2026, 1, 2)
    t_open = datetime(2026, 1, 2, 14, 30, tzinfo=UTC)
    t_close = datetime(2026, 1, 2, 21, 0, tzinfo=UTC)
    t_decision = datetime(2026, 1, 2, 21, 5, tzinfo=UTC)

    e1 = RebalanceDecisionEvent(session, t_decision, EventPriority.REBALANCE_DECISION, "s1")
    e2 = MarketOpenEvent(session, t_open, EventPriority.MARKET_OPEN)
    e3 = MarketCloseEvent(session, t_close, EventPriority.MARKET_CLOSE)

    # Supply out of order
    ordered = EventSequencer.sequence([e1, e3, e2])

    assert ordered == (e2, e3, e1)
