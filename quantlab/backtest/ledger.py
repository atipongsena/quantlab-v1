"""Append-only accounting ledgers for cash, positions, transactions, and corporate actions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from quantlab.domain.identity import InstrumentId


class TransactionType(StrEnum):
    INITIAL_CASH = "initial_cash"
    BUY_FILL = "buy_fill"
    SELL_FILL = "sell_fill"
    COMMISSION_FEE = "commission_fee"
    DIVIDEND_PAYMENT = "dividend_payment"
    SPLIT_ADJUSTMENT = "split_adjustment"
    DELISTING_SETTLEMENT = "delisting_settlement"


@dataclass(frozen=True, slots=True)
class CashTransaction:
    transaction_id: str
    timestamp: datetime
    transaction_type: TransactionType
    amount: Decimal
    balance_after: Decimal
    instrument_id: InstrumentId | None = None
    description: str = ""


@dataclass(frozen=True, slots=True)
class PositionLot:
    """Represents a position holding with weighted average cost basis."""

    instrument_id: InstrumentId
    quantity: Decimal
    cost_basis_per_share: Decimal

    @property
    def total_cost(self) -> Decimal:
        return (self.quantity * self.cost_basis_per_share).quantize(Decimal("0.0001"))


class CashLedger:
    """Immutable, append-only cash ledger tracking every inflow and outflow."""

    def __init__(self, initial_cash: Decimal = Decimal("1000000.00")) -> None:
        self._initial_cash = initial_cash
        self._current_balance = initial_cash
        self._transactions: list[CashTransaction] = []

    @property
    def balance(self) -> Decimal:
        return self._current_balance

    @property
    def transactions(self) -> tuple[CashTransaction, ...]:
        return tuple(self._transactions)

    def record(
        self,
        transaction_id: str,
        timestamp: datetime,
        transaction_type: TransactionType,
        amount: Decimal,
        instrument_id: InstrumentId | None = None,
        description: str = "",
    ) -> CashTransaction:
        new_balance = (self._current_balance + amount).quantize(Decimal("0.01"))
        tx = CashTransaction(
            transaction_id=transaction_id,
            timestamp=timestamp,
            transaction_type=transaction_type,
            amount=amount,
            balance_after=new_balance,
            instrument_id=instrument_id,
            description=description,
        )
        self._transactions.append(tx)
        self._current_balance = new_balance
        return tx


class PositionLedger:
    """Tracks active holdings and maintains weighted-average cost basis accounting."""

    def __init__(self) -> None:
        self._positions: dict[InstrumentId, PositionLot] = {}
        self._realized_pnl: Decimal = Decimal("0.0")

    @property
    def positions(self) -> dict[InstrumentId, PositionLot]:
        return dict(self._positions)

    @property
    def total_realized_pnl(self) -> Decimal:
        return self._realized_pnl

    def get_quantity(self, instrument_id: InstrumentId) -> Decimal:
        lot = self._positions.get(instrument_id)
        return lot.quantity if lot is not None else Decimal("0.0")

    def apply_buy(
        self, instrument_id: InstrumentId, quantity: Decimal, price: Decimal
    ) -> PositionLot:
        current_lot = self._positions.get(instrument_id)
        if current_lot is None or current_lot.quantity == Decimal("0.0"):
            new_lot = PositionLot(
                instrument_id=instrument_id,
                quantity=quantity,
                cost_basis_per_share=price,
            )
        else:
            old_qty = current_lot.quantity
            new_qty = old_qty + quantity
            total_cost = (old_qty * current_lot.cost_basis_per_share) + (quantity * price)
            avg_cost = (total_cost / new_qty).quantize(Decimal("0.0001"))
            new_lot = PositionLot(
                instrument_id=instrument_id,
                quantity=new_qty,
                cost_basis_per_share=avg_cost,
            )

        self._positions[instrument_id] = new_lot
        return new_lot

    def apply_sell(
        self, instrument_id: InstrumentId, quantity: Decimal, price: Decimal
    ) -> tuple[PositionLot | None, Decimal]:
        current_lot = self._positions.get(instrument_id)
        if current_lot is None or current_lot.quantity < quantity:
            curr_qty = current_lot.quantity if current_lot else Decimal("0.0")
            raise ValueError(
                f"Cannot sell {quantity} shares of {instrument_id}: current holding is {curr_qty}"
            )

        # Realized PnL = quantity * (price - cost_basis_per_share)
        cost_basis = current_lot.cost_basis_per_share
        realized = ((price - cost_basis) * quantity).quantize(Decimal("0.01"))
        self._realized_pnl = (self._realized_pnl + realized).quantize(Decimal("0.01"))

        remaining_qty = current_lot.quantity - quantity
        if remaining_qty == Decimal("0.0"):
            del self._positions[instrument_id]
            return None, realized

        new_lot = PositionLot(
            instrument_id=instrument_id,
            quantity=remaining_qty,
            cost_basis_per_share=cost_basis,
        )
        self._positions[instrument_id] = new_lot
        return new_lot, realized

    def apply_split(self, instrument_id: InstrumentId, split_ratio: Decimal) -> PositionLot | None:
        """Adjusts share quantity by split_ratio and cost basis inversely."""
        current_lot = self._positions.get(instrument_id)
        if current_lot is None or current_lot.quantity == Decimal("0.0"):
            return None

        new_qty = (current_lot.quantity * split_ratio).quantize(Decimal("0.0001"))
        new_cost = (current_lot.cost_basis_per_share / split_ratio).quantize(Decimal("0.0001"))

        new_lot = PositionLot(
            instrument_id=instrument_id,
            quantity=new_qty,
            cost_basis_per_share=new_cost,
        )
        self._positions[instrument_id] = new_lot
        return new_lot
