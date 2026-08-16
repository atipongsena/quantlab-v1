"""Deterministic historical simulation clock."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from datetime import date, timedelta

from quantlab.backtest.calendar import TradingCalendar
from quantlab.backtest.events import (
    EventPriority,
    MarketCloseEvent,
    MarketOpenEvent,
    RebalanceDecisionEvent,
    SimulationEvent,
)


class HistoricalClock:
    """Produces a deterministic stream of simulation session events without wall-clock.

    Generates market open, close, and rebalance decision events for each session.
    """

    def __init__(
        self,
        sessions: Sequence[date],
        rebalance_sessions: Sequence[date] | None = None,
        strategy_id: str = "default_strategy",
    ) -> None:
        self._sessions = tuple(sorted(sessions))
        self._rebalance_sessions = set(rebalance_sessions) if rebalance_sessions else set()
        self._strategy_id = strategy_id

    @property
    def sessions(self) -> tuple[date, ...]:
        return self._sessions

    def events(self) -> Iterator[SimulationEvent]:
        """Yield simulation lifecycle events for all sessions in order."""
        for session in self._sessions:
            open_utc = TradingCalendar.session_open_utc(session)
            close_utc = TradingCalendar.session_close_utc(session)

            # 1. Market Open
            yield MarketOpenEvent(
                session=session,
                timestamp=open_utc,
                priority=EventPriority.MARKET_OPEN,
            )

            # 2. Market Close
            yield MarketCloseEvent(
                session=session,
                timestamp=close_utc,
                priority=EventPriority.MARKET_CLOSE,
            )

            # 3. Post-Close Rebalance Decision (if scheduled)
            if session in self._rebalance_sessions:
                decision_utc = close_utc + timedelta(minutes=5)
                yield RebalanceDecisionEvent(
                    session=session,
                    timestamp=decision_utc,
                    priority=EventPriority.REBALANCE_DECISION,
                    strategy_id=self._strategy_id,
                )
