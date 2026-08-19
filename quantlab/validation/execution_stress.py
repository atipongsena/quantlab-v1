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

    # Above this the break-even figure stops being informative: no realistic friction
    # assumption reaches it, and quoting a precise number implies a precision the linear
    # cost model does not have.
    BREAK_EVEN_CAP_BPS = 1000.0

    @classmethod
    def evaluate(
        cls,
        zero_cost_cagr: float,
        turnover_annual: float,
        annualized_volatility: float = 0.15,
        cost_bps_grid: tuple[float, ...] = (0.0, 5.0, 10.0, 20.0, 50.0, 100.0),
    ) -> ExecutionStressResult:
        """Sweep transaction costs and find where the edge disappears.

        Cost enters as a linear drag of ``turnover x cost x 2`` on the annual return,
        which is the first-order approximation: it ignores that higher costs would also
        change which trades the strategy chooses to make, so treat the break-even as an
        upper bound on how much friction the edge survives, not a guarantee.
        """
        sharpe_map: dict[float, float] = {}
        cagr_map: dict[float, float] = {}
        vol = annualized_volatility if annualized_volatility > 1e-6 else 0.15

        for cost_bps in cost_bps_grid:
            cost_drag = turnover_annual * (cost_bps / 10000.0) * 2.0  # roundtrip cost
            net_cagr = zero_cost_cagr - cost_drag
            cagr_map[cost_bps] = round(net_cagr, 4)
            sharpe_map[cost_bps] = round(net_cagr / vol, 2)

        # Break even cost: cost where net_cagr == 0
        if turnover_annual > 1e-4 and zero_cost_cagr > 0:
            break_even = min(
                (zero_cost_cagr / (turnover_annual * 2.0)) * 10000.0,
                cls.BREAK_EVEN_CAP_BPS,
            )
        elif zero_cost_cagr <= 0:
            break_even = 0.0
        else:
            break_even = cls.BREAK_EVEN_CAP_BPS

        is_fragile = break_even < 10.0  # Edge disappears below 10 bps friction

        return ExecutionStressResult(
            cost_bps_grid=cost_bps_grid,
            sharpe_by_cost=sharpe_map,
            cagr_by_cost=cagr_map,
            break_even_cost_bps=round(break_even, 1),
            is_cost_fragile=is_fragile,
        )
