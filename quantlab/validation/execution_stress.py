"""Execution friction stress testing and break-even cost analysis."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExecutionStressResult:
    cost_bps_grid: tuple[float, ...]
    sharpe_by_cost: Mapping[float, float]
    cagr_by_cost: Mapping[float, float]
    break_even_cost_bps: float
    is_cost_fragile: bool


class ExecutionStressTester:
    """Stress tests strategy returns across adverse execution cost assumptions."""

    @classmethod
    def evaluate(
        cls,
        zero_cost_cagr: float,
        turnover_annual: float,
        cost_bps_grid: tuple[float, ...] = (0.0, 5.0, 10.0, 20.0, 50.0),
    ) -> ExecutionStressResult:
        sharpe_map: dict[float, float] = {}
        cagr_map: dict[float, float] = {}

        for cost_bps in cost_bps_grid:
            cost_drag = turnover_annual * (cost_bps / 10000.0) * 2.0  # roundtrip cost
            net_cagr = zero_cost_cagr - cost_drag
            # Approximate Sharpe assuming 15% constant annualized vol
            net_sharpe = net_cagr / 0.15

            cagr_map[cost_bps] = round(net_cagr, 4)
            sharpe_map[cost_bps] = round(net_sharpe, 2)

        # Break even cost: cost where net_cagr == 0
        if turnover_annual > 1e-4:
            break_even = (zero_cost_cagr / (turnover_annual * 2.0)) * 10000.0
        else:
            break_even = 999.0

        is_fragile = break_even < 10.0  # Edge disappears below 10 bps friction

        return ExecutionStressResult(
            cost_bps_grid=cost_bps_grid,
            sharpe_by_cost=sharpe_map,
            cagr_by_cost=cagr_map,
            break_even_cost_bps=round(break_even, 1),
            is_cost_fragile=is_fragile,
        )
