"""Factor ablation and contribution analysis."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AblationRecord:
    omitted_factor: str
    sharpe_ratio: float
    cagr: float
    marginal_contribution_sharpe: float


class AblationAnalyzer:
    """Computes marginal contribution of each constituent factor in a composite."""

    @classmethod
    def evaluate(
        cls,
        baseline_sharpe: float,
        baseline_cagr: float,
        ablation_results: Mapping[str, tuple[float, float]],  # factor_name -> (sharpe, cagr)
    ) -> tuple[AblationRecord, ...]:
        records: list[AblationRecord] = []
        for factor_name, (ablated_sharpe, ablated_cagr) in ablation_results.items():
            # Marginal contribution = baseline - ablated performance
            marginal_sharpe = baseline_sharpe - ablated_sharpe
            records.append(
                AblationRecord(
                    omitted_factor=factor_name,
                    sharpe_ratio=ablated_sharpe,
                    cagr=ablated_cagr,
                    marginal_contribution_sharpe=round(marginal_sharpe, 4),
                )
            )
        return tuple(records)
