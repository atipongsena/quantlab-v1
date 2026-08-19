"""Authoritative accounting engine enforcing Decimal conservation."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from quantlab.backtest.corporate_actions import CorporateActionProcessor
from quantlab.backtest.ledger import CashLedger, PositionLedger, TransactionType
from quantlab.backtest.marking import mark_to_market
from quantlab.domain.corporate_actions import CorporateAction
from quantlab.domain.identity import InstrumentId
from quantlab.domain.orders import Fill, OrderSide
from quantlab.domain.portfolio import PortfolioSnapshot


@dataclass(frozen=True, slots=True)
class AccountingState:
    portfolio_id: str
    cash_balance: Decimal
    total_realized_pnl: Decimal
    unrealized_pnl: Decimal
    total_equity: Decimal


class AccountingEngine:
    """Core portfolio accounting engine with full auditability."""

    def __init__(
        self,
        portfolio_id: str = "PORT-MAIN",
        initial_cash: Decimal = Decimal("1000000.00"),
    ) -> None:
        self._portfolio_id = portfolio_id
        self._cash_ledger = CashLedger(initial_cash)
        self._position_ledger = PositionLedger()

    @property
    def portfolio_id(self) -> str:
        return self._portfolio_id

    @property
    def cash_ledger(self) -> CashLedger:
        return self._cash_ledger

    @property
    def position_ledger(self) -> PositionLedger:
        return self._position_ledger

    def apply_fill(self, fill: Fill, side: OrderSide) -> None:
        """Process an executed trade fill through cash and position ledgers."""
        inst = fill.instrument_id
        qty = fill.quantity
        price = fill.price
        fees = fill.fees

        if side == OrderSide.BUY:
            total_cash_outflow = ((qty * price) + fees).quantize(Decimal("0.01"))
            self._cash_ledger.record(
                transaction_id=f"TX-{uuid.uuid4().hex[:12]}",
                timestamp=fill.filled_at,
                transaction_type=TransactionType.BUY_FILL,
                amount=-total_cash_outflow,
                instrument_id=inst,
                description=f"Buy {qty} @ {price} (fees: {fees})",
            )
            self._position_ledger.apply_buy(inst, qty, price)

        elif side == OrderSide.SELL:
            gross_proceeds = qty * price
            net_cash_inflow = (gross_proceeds - fees).quantize(Decimal("0.01"))
            self._cash_ledger.record(
                transaction_id=f"TX-{uuid.hex if hasattr(uuid, 'hex') else uuid.uuid4().hex[:12]}",
                timestamp=fill.filled_at,
                transaction_type=TransactionType.SELL_FILL,
                amount=net_cash_inflow,
                instrument_id=inst,
                description=f"Sell {qty} @ {price} (fees: {fees})",
            )
            self._position_ledger.apply_sell(inst, qty, price)

    def apply_corporate_action(self, action: CorporateAction, effective_time: datetime) -> None:
        CorporateActionProcessor.apply(
            action=action,
            cash_ledger=self._cash_ledger,
            position_ledger=self._position_ledger,
            effective_time=effective_time,
        )

    def mark_to_market(
        self,
        as_of: datetime,
        close_prices: Mapping[InstrumentId, Decimal],
        last_known_prices: Mapping[InstrumentId, Decimal] | None = None,
    ) -> PortfolioSnapshot:
        return mark_to_market(
            portfolio_id=self._portfolio_id,
            as_of=as_of,
            cash_ledger=self._cash_ledger,
            position_ledger=self._position_ledger,
            close_prices=close_prices,
            last_known_prices=last_known_prices,
        )
