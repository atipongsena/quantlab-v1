"""Simulated broker executing market orders with slippage, fees, and participation limits."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from quantlab.backtest.costs import FeeModel, SlippageModel
from quantlab.backtest.execution import NextOpenExecution
from quantlab.backtest.order_state import OrderStateMachine
from quantlab.backtest.participation import VolumeParticipationModel
from quantlab.domain.market import MarketBar
from quantlab.domain.orders import Fill, Order, OrderState


class SimulatedBroker:
    """Simulates realistic broker fills at next-session market open."""

    def __init__(
        self,
        slippage_model: SlippageModel | None = None,
        fee_model: FeeModel | None = None,
        participation_model: VolumeParticipationModel | None = None,
    ) -> None:
        self._slippage_model = slippage_model or SlippageModel()
        self._fee_model = fee_model or FeeModel()
        self._participation_model = participation_model

    def execute_order(
        self,
        order: Order,
        bar: MarketBar | None,
        session: date,
        fill_time: datetime,
    ) -> tuple[Order, Fill | None]:
        """Execute a market order against a market bar."""
        if order.state in (OrderState.FILLED, OrderState.CANCELLED, OrderState.REJECTED):
            return order, None

        # Transition CREATED to SUBMITTED first if needed
        active_order = (
            OrderStateMachine.transition(order, OrderState.SUBMITTED, transitioned_at=fill_time)
            if order.state == OrderState.CREATED
            else order
        )

        # If bar is missing or missing valid open price -> reject order
        if bar is None:
            rejected = OrderStateMachine.transition(
                active_order, OrderState.REJECTED, transitioned_at=fill_time
            )
            return rejected, None

        ref_price = NextOpenExecution.reference_price(active_order, bar)
        if ref_price is None or ref_price <= Decimal("0.0"):
            rejected = OrderStateMachine.transition(
                active_order, OrderState.REJECTED, transitioned_at=fill_time
            )
            return rejected, None

        # Determine executable quantity based on volume participation cap
        qty_to_fill = active_order.quantity
        if self._participation_model is not None:
            max_qty = self._participation_model.max_executable_quantity(bar.volume)
            if max_qty <= Decimal("0.0"):
                # No volume available to fill
                return active_order, None
            if qty_to_fill > max_qty:
                qty_to_fill = max_qty

        # Calculate slipped price and fees
        exec_price, _ = self._slippage_model.execute_price(ref_price, active_order.side)
        fees = self._fee_model.calculate_fees(qty_to_fill, exec_price)

        # Transition order state
        next_state = (
            OrderState.FILLED
            if qty_to_fill >= active_order.quantity
            else OrderState.PARTIALLY_FILLED
        )
        updated_order = OrderStateMachine.transition(
            active_order, next_state, transitioned_at=fill_time
        )

        fill = Fill(
            fill_id=f"FILL-{uuid.uuid4().hex[:12]}",
            order_id=active_order.order_id,
            instrument_id=active_order.instrument_id,
            filled_at=fill_time,
            quantity=qty_to_fill,
            price=exec_price,
            fees=fees,
            source="simulated_broker",
        )

        return updated_order, fill
