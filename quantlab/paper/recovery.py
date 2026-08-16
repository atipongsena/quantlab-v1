"""Disaster recovery and state reconstruction engine from fills replay."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from quantlab.domain.identity import InstrumentId
from quantlab.paper.contracts import BrokerAccount, PaperFill, PaperOrderSide


class DisasterRecoveryEngine:
    """Reconstructs exact point-in-time account cash and positions by replaying immutable fills."""

    @classmethod
    def reconstruct_from_fills(
        cls,
        account_id: str,
        initial_cash: Decimal,
        fills: Sequence[PaperFill],
    ) -> BrokerAccount:
        cash = initial_cash
        positions: dict[InstrumentId, Decimal] = {}

        # Sort fills chronologically
        sorted_fills = sorted(fills, key=lambda f: f.filled_at)

        for f in sorted_fills:
            notional = f.price * Decimal(f.quantity)
            if f.side == PaperOrderSide.BUY:
                cash -= notional + f.commission
                cur_qty = positions.get(f.instrument_id, Decimal("0"))
                positions[f.instrument_id] = cur_qty + Decimal(f.quantity)
            else:
                cash += notional - f.commission
                cur_qty = positions.get(f.instrument_id, Decimal("0"))
                new_qty = cur_qty - Decimal(f.quantity)
                if new_qty <= 0:
                    positions.pop(f.instrument_id, None)
                else:
                    positions[f.instrument_id] = new_qty

        return BrokerAccount(
            account_id=account_id,
            cash_balance=cash,
            buying_power=cash,
            positions=positions,
        )
