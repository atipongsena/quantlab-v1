"""Order state machine and transition enforcement."""

from __future__ import annotations

from datetime import datetime

from quantlab.domain.orders import (
    ORDER_STATE_TRANSITIONS,
    TERMINAL_ORDER_STATES,
    Order,
    OrderState,
)


class OrderStateMachine:
    """Enforces deterministic order lifecycle transitions."""

    @classmethod
    def can_transition(cls, current: OrderState, next_state: OrderState) -> bool:
        if current in TERMINAL_ORDER_STATES:
            return False
        return next_state in ORDER_STATE_TRANSITIONS[current]

    @classmethod
    def transition(cls, order: Order, next_state: OrderState, transitioned_at: datetime) -> Order:
        return order.transition_to(next_state, transitioned_at=transitioned_at)
