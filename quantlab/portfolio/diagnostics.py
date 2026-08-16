"""Pre-trade portfolio analytics and concentration diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from quantlab.domain.portfolio import TargetPortfolio


@dataclass(frozen=True, slots=True)
class PreTradeDiagnostics:
    active_names: int
    gross_exposure: Decimal
    cash_buffer: Decimal
    max_position_weight: Decimal
    herfindahl_index: Decimal
    effective_number_of_bets: Decimal


def compute_pre_trade_diagnostics(
    target: TargetPortfolio,
    gross_cap: Decimal = Decimal("1.0"),
) -> PreTradeDiagnostics:
    """Compute concentration and diversification diagnostics."""
    weights = [p.target_weight for p in target.positions if p.target_weight > Decimal("0.0")]
    active_names = len(weights)
    gross_exposure = sum(weights, Decimal("0.0"))
    cash_buffer = gross_cap - gross_exposure
    max_weight = max(weights) if weights else Decimal("0.0")

    # Herfindahl-Hirschman Index (HHI) sum(w_i^2)
    hhi = sum((w * w for w in weights), Decimal("0.0"))
    effective_bets = Decimal("0.0")
    if hhi > Decimal("0.0"):
        effective_bets = (Decimal("1.0") / hhi).quantize(Decimal("0.01"))

    return PreTradeDiagnostics(
        active_names=active_names,
        gross_exposure=gross_exposure,
        cash_buffer=cash_buffer,
        max_position_weight=max_weight,
        herfindahl_index=hhi.quantize(Decimal("0.0001")),
        effective_number_of_bets=effective_bets,
    )
