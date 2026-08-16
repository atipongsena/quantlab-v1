"""Broker adapter interface and deterministic mock execution adapter."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from decimal import Decimal
from typing import Protocol

from quantlab.domain.identity import InstrumentId
from quantlab.paper.contracts import (
    BrokerAccount,
    PaperFill,
    PaperOrder,
    PaperOrderSide,
    PaperOrderStatus,
)


class BrokerAdapter(Protocol):
    """Protocol for interacting with paper and execution brokers."""

    def get_account(self) -> BrokerAccount: ...
    def get_positions(self) -> Mapping[InstrumentId, Decimal]: ...
    def submit_order(self, order: PaperOrder) -> tuple[PaperOrder, tuple[PaperFill, ...]]: ...


class MockExecutionAdapter:
    """In-memory mock broker execution adapter for paper trading simulations."""

    def __init__(
        self,
        account_id: str = "PAPER-ACCT-01",
        initial_cash: Decimal = Decimal("1000000.00"),
        slippage_bps: Decimal = Decimal("5.0"),
        commission_per_order: Decimal = Decimal("1.00"),
    ) -> None:
        self.account_id = account_id
        self._cash = initial_cash
        self._positions: dict[InstrumentId, Decimal] = {}
        self._prices: dict[InstrumentId, Decimal] = {}
        self.slippage_bps = slippage_bps
        self.commission_per_order = commission_per_order

    def set_prices(self, prices: Mapping[InstrumentId, Decimal]) -> None:
        self._prices.update(prices)

    def get_account(self) -> BrokerAccount:
        # Buying power = cash
        return BrokerAccount(
            account_id=self.account_id,
            cash_balance=self._cash,
            buying_power=self._cash,
            positions=dict(self._positions),
        )

    def get_positions(self) -> Mapping[InstrumentId, Decimal]:
        return dict(self._positions)

    def submit_order(self, order: PaperOrder) -> tuple[PaperOrder, tuple[PaperFill, ...]]:
        price = self._prices.get(order.instrument_id, Decimal("100.00"))
        # Adverse slippage
        slip_multiplier = (
            (Decimal("1.0") + self.slippage_bps / Decimal("10000.0"))
            if order.side == PaperOrderSide.BUY
            else (Decimal("1.0") - self.slippage_bps / Decimal("10000.0"))
        )
        fill_price = round(price * slip_multiplier, 4)

        fill = PaperFill(
            fill_id=f"FILL-{uuid.uuid4().hex[:10]}",
            order_id=order.order_id,
            instrument_id=order.instrument_id,
            side=order.side,
            quantity=order.quantity,
            price=fill_price,
            commission=self.commission_per_order,
            filled_at=datetime.now(tz=UTC),
        )

        # Update cash and positions
        notional = fill_price * Decimal(order.quantity)
        if order.side == PaperOrderSide.BUY:
            self._cash -= notional + self.commission_per_order
            cur_qty = self._positions.get(order.instrument_id, Decimal("0"))
            self._positions[order.instrument_id] = cur_qty + Decimal(order.quantity)
        else:
            self._cash += notional - self.commission_per_order
            cur_qty = self._positions.get(order.instrument_id, Decimal("0"))
            new_qty = cur_qty - Decimal(order.quantity)
            if new_qty <= 0:
                self._positions.pop(order.instrument_id, None)
            else:
                self._positions[order.instrument_id] = new_qty

        filled_order = PaperOrder(
            order_id=order.order_id,
            session=order.session,
            instrument_id=order.instrument_id,
            side=order.side,
            quantity=order.quantity,
            order_type=order.order_type,
            status=PaperOrderStatus.FILLED,
        )

        return filled_order, (fill,)
