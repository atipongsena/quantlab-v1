"""Portfolio concentration risk analysis."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal

from quantlab.domain.identity import InstrumentId


@dataclass(frozen=True, slots=True)
class ConcentrationRiskReport:
    herfindahl_index: float
    effective_number_of_bets: float
    top_5_holding_weight_pct: float
    top_sector_weight_pct: float
    is_excessively_concentrated: bool


class ConcentrationAnalyzer:
    """Computes concentration metrics and assesses single-stock / sector dependency."""

    @classmethod
    def evaluate(
        cls,
        position_weights: Mapping[InstrumentId, Decimal],
        sector_weights: Mapping[str, Decimal],
        max_hhi_threshold: float = 0.15,
    ) -> ConcentrationRiskReport:
        w_floats = [float(w) for w in position_weights.values() if w > 0]
        if not w_floats:
            return ConcentrationRiskReport(
                herfindahl_index=0.0,
                effective_number_of_bets=0.0,
                top_5_holding_weight_pct=0.0,
                top_sector_weight_pct=0.0,
                is_excessively_concentrated=False,
            )

        hhi = sum(w**2 for w in w_floats)
        effective_bets = (1.0 / hhi) if hhi > 1e-6 else 0.0

        sorted_w = sorted(w_floats, reverse=True)
        top_5_pct = sum(sorted_w[:5]) * 100.0

        sec_floats = [float(w) for w in sector_weights.values()]
        top_sec_pct = (max(sec_floats) * 100.0) if sec_floats else 0.0

        is_concentrated = hhi > max_hhi_threshold or top_sec_pct > 40.0

        return ConcentrationRiskReport(
            herfindahl_index=round(hhi, 4),
            effective_number_of_bets=round(effective_bets, 2),
            top_5_holding_weight_pct=round(top_5_pct, 2),
            top_sector_weight_pct=round(top_sec_pct, 2),
            is_excessively_concentrated=is_concentrated,
        )
