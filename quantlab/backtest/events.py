"""Simulation event contracts and strict priority sequencing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import IntEnum

from quantlab.domain.corporate_actions import CorporateAction
from quantlab.domain.market import MarketBar
from quantlab.domain.orders import Fill, Order


class EventPriority(IntEnum):
    CORPORATE_ACTION = 10
    MARKET_OPEN = 20
    BAR = 30
    MARKET_CLOSE = 40
    REBALANCE_DECISION = 50


@dataclass(frozen=True, slots=True)
class SimulationEvent:
    session: date
    timestamp: datetime
    priority: EventPriority

    def __lt__(self, other: SimulationEvent) -> bool:
        if self.timestamp != other.timestamp:
            return self.timestamp < other.timestamp
        return self.priority < other.priority


@dataclass(frozen=True, slots=True)
class CorporateActionEvent(SimulationEvent):
    action: CorporateAction


@dataclass(frozen=True, slots=True)
class MarketOpenEvent(SimulationEvent):
    pass


@dataclass(frozen=True, slots=True)
class MarketCloseEvent(SimulationEvent):
    pass


@dataclass(frozen=True, slots=True)
class RebalanceDecisionEvent(SimulationEvent):
    strategy_id: str


@dataclass(frozen=True, slots=True)
class BarEvent(SimulationEvent):
    bar: MarketBar


@dataclass(frozen=True, slots=True)
class OrderEvent(SimulationEvent):
    order: Order


@dataclass(frozen=True, slots=True)
class FillEvent(SimulationEvent):
    fill: Fill
