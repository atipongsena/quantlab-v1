"""Performance attribution and return decomposition."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal


def brinson_allocation_selection(
    portfolio_weights: Mapping[str, Decimal],
    benchmark_weights: Mapping[str, Decimal],
    portfolio_returns: Mapping[str, Decimal],
    benchmark_returns: Mapping[str, Decimal],
) -> dict[str, Decimal]:
    """Computes Brinson allocation and selection effects by sector."""
    sectors = set(portfolio_weights.keys()) | set(benchmark_weights.keys())
    bm_terms = (
        benchmark_weights.get(s, Decimal("0.0")) * benchmark_returns.get(s, Decimal("0.0"))
        for s in sectors
    )
    bm_total_ret = sum(bm_terms, Decimal("0.0"))

    allocation_effect = Decimal("0.0")
    selection_effect = Decimal("0.0")

    for s in sectors:
        wp = portfolio_weights.get(s, Decimal("0.0"))
        wb = benchmark_weights.get(s, Decimal("0.0"))
        rp = portfolio_returns.get(s, Decimal("0.0"))
        rb = benchmark_returns.get(s, Decimal("0.0"))

        allocation_effect += (wp - wb) * (rb - bm_total_ret)
        selection_effect += wb * (rp - rb)

    return {
        "allocation_effect": allocation_effect.quantize(Decimal("0.0001")),
        "selection_effect": selection_effect.quantize(Decimal("0.0001")),
        "total_active_return": (allocation_effect + selection_effect).quantize(Decimal("0.0001")),
    }
