"""Deterministic event sorting and sequencing."""

from __future__ import annotations

from collections.abc import Iterable

from quantlab.backtest.events import SimulationEvent


class EventSequencer:
    """Sorts simulation events into strict, reproducible chronological sequence."""

    @classmethod
    def sequence(cls, events: Iterable[SimulationEvent]) -> tuple[SimulationEvent, ...]:
        """Sort events by timestamp ascending, priority ascending."""
        return tuple(sorted(events, key=lambda e: (e.timestamp, int(e.priority))))
