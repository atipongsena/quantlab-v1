"""Mark-to-market valuation and portfolio snapshot generation."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal

from quantlab.backtest.ledger import CashLedger, PositionLedger
from quantlab.domain.identity import InstrumentId
from quantlab.domain.portfolio import PortfolioSnapshot, Position


def mark_to_market(
    portfolio_id: str,
    as_of: datetime,
    cash_ledger: CashLedger,
    position_ledger: PositionLedger,
    close_prices: Mapping[InstrumentId, Decimal],
) -> PortfolioSnapshot:
    """Computes mark-to-market valuations and builds an authoritative PortfolioSnapshot."""
    positions_list: list[Position] = []

    # Sort instruments by UUID string for determinism
    for inst, lot in sorted(position_ledger.positions.items(), key=lambda item: str(item[0].value)):
        if lot.quantity <= Decimal("0.0"):
            continue

        price = close_prices.get(inst)
        if price is None or price <= Decimal("0.0"):
            price = lot.cost_basis_per_share

        mkt_val = (lot.quantity * price).quantize(Decimal("0.01"))
        cost_basis = lot.total_cost.quantize(Decimal("0.01"))

        positions_list.append(
            Position(
                instrument_id=inst,
                quantity=lot.quantity,
                cost_basis=cost_basis,
                market_value=mkt_val,
            )
        )

    return PortfolioSnapshot(
        portfolio_id=portfolio_id,
        as_of=as_of,
        cash=cash_ledger.balance,
        positions=tuple(positions_list),
    )
