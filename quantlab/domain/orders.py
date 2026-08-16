from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from quantlab.domain.identity import (
    InstrumentId,
    _require_nonempty,
    require_nonnegative_decimal,
    require_positive_decimal,
    require_timezone_aware,
)


class OrderSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class OrderType(StrEnum):
    MARKET = "market"
    LIMIT = "limit"


class OrderState(StrEnum):
    CREATED = "created"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


TERMINAL_ORDER_STATES = frozenset({OrderState.FILLED, OrderState.CANCELLED, OrderState.REJECTED})
ORDER_STATE_TRANSITIONS: dict[OrderState, frozenset[OrderState]] = {
    OrderState.CREATED: frozenset(
        {OrderState.SUBMITTED, OrderState.CANCELLED, OrderState.REJECTED}
    ),
    OrderState.SUBMITTED: frozenset(
        {
            OrderState.PARTIALLY_FILLED,
            OrderState.FILLED,
            OrderState.CANCELLED,
            OrderState.REJECTED,
        }
    ),
    OrderState.PARTIALLY_FILLED: frozenset({OrderState.FILLED, OrderState.CANCELLED}),
    OrderState.FILLED: frozenset(),
    OrderState.CANCELLED: frozenset(),
    OrderState.REJECTED: frozenset(),
}


@dataclass(frozen=True, slots=True)
class Order:
    order_id: str
    instrument_id: InstrumentId
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    state: OrderState
    created_at: datetime
    limit_price: Decimal | None = None
    state_updated_at: datetime | None = None

    def __post_init__(self) -> None:
        _require_nonempty(self.order_id, "order_id")
        if not isinstance(self.instrument_id, InstrumentId):
            raise TypeError("instrument_id must be InstrumentId")
        if not isinstance(self.side, OrderSide):
            raise TypeError("side must be OrderSide")
        if not isinstance(self.order_type, OrderType):
            raise TypeError("order_type must be OrderType")
        require_positive_decimal(self.quantity, "quantity")
        if not isinstance(self.state, OrderState):
            raise TypeError("state must be OrderState")
        require_timezone_aware(self.created_at, "created_at")
        if self.limit_price is not None:
            require_positive_decimal(self.limit_price, "limit_price")
        if self.state_updated_at is not None:
            require_timezone_aware(self.state_updated_at, "state_updated_at")
            if self.state_updated_at < self.created_at:
                raise ValueError("state_updated_at must be on or after created_at")
        if self.order_type is OrderType.LIMIT and self.limit_price is None:
            raise ValueError("limit orders require limit_price")

    def transition_to(self, next_state: OrderState, *, transitioned_at: datetime) -> Order:
        if not isinstance(next_state, OrderState):
            raise TypeError("next_state must be OrderState")
        require_timezone_aware(transitioned_at, "transitioned_at")
        if self.state in TERMINAL_ORDER_STATES:
            if next_state is self.state:
                return self
            raise ValueError("terminal order state cannot transition")
        if next_state not in ORDER_STATE_TRANSITIONS[self.state]:
            raise ValueError(f"illegal order state transition: {self.state} -> {next_state}")
        if transitioned_at < self.created_at:
            raise ValueError("transitioned_at must be on or after created_at")
        return replace(self, state=next_state, state_updated_at=transitioned_at)


@dataclass(frozen=True, slots=True)
class Fill:
    fill_id: str
    order_id: str
    instrument_id: InstrumentId
    filled_at: datetime
    quantity: Decimal
    price: Decimal
    fees: Decimal
    source: str

    def __post_init__(self) -> None:
        _require_nonempty(self.fill_id, "fill_id")
        _require_nonempty(self.order_id, "order_id")
        if not isinstance(self.instrument_id, InstrumentId):
            raise TypeError("instrument_id must be InstrumentId")
        require_timezone_aware(self.filled_at, "filled_at")
        require_positive_decimal(self.quantity, "quantity")
        require_positive_decimal(self.price, "price")
        require_nonnegative_decimal(self.fees, "fees")
        _require_nonempty(self.source, "source")
