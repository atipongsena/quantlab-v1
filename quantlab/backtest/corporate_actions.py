"""Corporate action handling for splits, dividends, and delistings."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from quantlab.backtest.ledger import CashLedger, PositionLedger, TransactionType
from quantlab.domain.corporate_actions import CorporateAction, CorporateActionType


class CorporateActionProcessor:
    """Applies corporate actions directly to cash and position ledgers."""

    @classmethod
    def apply(
        cls,
        action: CorporateAction,
        cash_ledger: CashLedger,
        position_ledger: PositionLedger,
        effective_time: datetime,
    ) -> None:
        inst_id = action.instrument_id
        qty = position_ledger.get_quantity(inst_id)
        if qty <= Decimal("0.0"):
            return

        if action.action_type == CorporateActionType.SPLIT:
            if action.ratio and action.ratio > Decimal("0.0"):
                position_ledger.apply_split(inst_id, action.ratio)

        elif action.action_type == CorporateActionType.DIVIDEND:
            if action.cash_amount and action.cash_amount > Decimal("0.0"):
                total_dividend = (qty * action.cash_amount).quantize(Decimal("0.01"))
                cash_ledger.record(
                    transaction_id=f"DIV-{uuid.uuid4().hex[:12]}",
                    timestamp=effective_time,
                    transaction_type=TransactionType.DIVIDEND_PAYMENT,
                    amount=total_dividend,
                    instrument_id=inst_id,
                    description=f"Dividend {action.cash_amount} on {qty} shares",
                )

        elif action.action_type == CorporateActionType.DELISTING:
            # Settle delisted shares
            settlement_price = action.cash_amount or Decimal("0.0")
            _, realized_pnl = position_ledger.apply_sell(inst_id, qty, settlement_price)
            cash_credit = (qty * settlement_price).quantize(Decimal("0.01"))
            if cash_credit > Decimal("0.0"):
                cash_ledger.record(
                    transaction_id=f"DELIST-{uuid.uuid4().hex[:12]}",
                    timestamp=effective_time,
                    transaction_type=TransactionType.DELISTING_SETTLEMENT,
                    amount=cash_credit,
                    instrument_id=inst_id,
                    description=f"Delisting liquidation at {settlement_price}",
                )
