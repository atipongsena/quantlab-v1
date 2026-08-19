"""Builders for validation fixtures used across the validation tests.

Robustness evidence now has to be measured rather than assumed, so tests that only care
about a downstream decision build an explicit artifact here instead of relying on the
runner to invent one.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from decimal import Decimal

from quantlab.domain.identity import InstrumentId
from quantlab.validation.candidate import FrozenCandidate
from quantlab.validation.robustness import RobustnessArtifact, RobustnessRunner
from quantlab.validation.sensitivity import SensitivityCell


def build_robustness(
    candidate: FrozenCandidate,
    top_k_sharpes: Mapping[int, float] | None = None,
    zero_cost_cagr: float = 0.18,
    annual_turnover: float = 3.0,
    ablation_results: Mapping[str, tuple[float, float]] | None = None,
    baseline_sharpe: float = 1.25,
    baseline_cagr: float = 0.18,
    positions: int = 30,
    sector_weights: Mapping[str, Decimal] | None = None,
    subperiod_cagr: Mapping[str, float] | None = None,
) -> RobustnessArtifact:
    sharpes = top_k_sharpes or {20: 1.15, 30: baseline_sharpe, 50: 1.10}
    cells: Sequence[SensitivityCell] = [
        SensitivityCell(
            parameters={"top_k": top_k},
            sharpe_ratio=sharpe,
            cagr=zero_cost_cagr,
            max_drawdown=0.12,
        )
        for top_k, sharpe in sorted(sharpes.items())
    ]

    weight = Decimal("1") / Decimal(positions)
    weights = {InstrumentId(uuid.UUID(int=i + 1)): weight for i in range(positions)}
    sectors = sector_weights or {
        "TECHNOLOGY": Decimal("0.30"),
        "HEALTHCARE": Decimal("0.25"),
        "FINANCIALS": Decimal("0.20"),
        "STAPLES": Decimal("0.25"),
    }

    return RobustnessRunner.run(
        candidate=candidate,
        top_k_cells=cells,
        zero_cost_cagr=zero_cost_cagr,
        annual_turnover=annual_turnover,
        terminal_weights=weights,
        sector_weights=sectors,
        ablation_results=ablation_results
        or {
            "momentum_12_1": (1.05, 0.14),
            "volatility_60d": (1.18, 0.16),
        },
        baseline_sharpe=baseline_sharpe,
        baseline_cagr=baseline_cagr,
        subperiod_cagr=subperiod_cagr,
    )
