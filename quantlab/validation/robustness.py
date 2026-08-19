"""Systematic robustness matrix and parameter stability runner."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal

from quantlab.domain.identity import InstrumentId
from quantlab.validation.ablation import AblationAnalyzer, AblationRecord
from quantlab.validation.candidate import FrozenCandidate
from quantlab.validation.concentration import ConcentrationAnalyzer, ConcentrationRiskReport
from quantlab.validation.execution_stress import ExecutionStressResult, ExecutionStressTester
from quantlab.validation.sensitivity import SensitivityCell, SensitivitySurface


@dataclass(frozen=True, slots=True)
class RobustnessArtifact:
    candidate_id: str
    top_k_surface: SensitivitySurface
    cost_stress: ExecutionStressResult
    concentration: ConcentrationRiskReport
    ablations: tuple[AblationRecord, ...]
    subperiod_cagr: Mapping[str, float]

    def as_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "top_k_topology": self.top_k_surface.topology.value,
            "top_k_cells": [
                {
                    "top_k": cell.parameters.get("top_k"),
                    "sharpe_ratio": round(cell.sharpe_ratio, 4),
                    "cagr": round(cell.cagr, 6),
                    "max_drawdown": round(cell.max_drawdown, 6),
                }
                for cell in self.top_k_surface.cells
            ],
            "break_even_cost_bps": self.cost_stress.break_even_cost_bps,
            "is_cost_fragile": self.cost_stress.is_cost_fragile,
            "herfindahl_index": self.concentration.herfindahl_index,
            "is_excessively_concentrated": self.concentration.is_excessively_concentrated,
            "ablations": [record.as_dict() for record in self.ablations],
            "ablations_count": len(self.ablations),
            "subperiod_cagr": {k: round(v, 6) for k, v in self.subperiod_cagr.items()},
        }


class RobustnessRunner:
    """Assembles the robustness matrix from measurements the caller supplies.

    Every input here has to come from a real re-run of the strategy. A hard-coded
    sensitivity surface will always report a reassuring plateau, which is worse than
    having no surface at all: it looks like evidence.
    """

    @classmethod
    def run(
        cls,
        candidate: FrozenCandidate,
        top_k_cells: Sequence[SensitivityCell],
        zero_cost_cagr: float,
        annual_turnover: float,
        terminal_weights: Mapping[InstrumentId, Decimal],
        sector_weights: Mapping[str, Decimal],
        ablation_results: Mapping[str, tuple[float, float]],
        baseline_sharpe: float,
        baseline_cagr: float,
        subperiod_cagr: Mapping[str, float] | None = None,
    ) -> RobustnessArtifact:
        top_k_surface = SensitivitySurface.analyze("top_k", list(top_k_cells))

        cost_stress = ExecutionStressTester.evaluate(
            zero_cost_cagr=zero_cost_cagr,
            turnover_annual=annual_turnover,
        )

        concentration = ConcentrationAnalyzer.evaluate(dict(terminal_weights), dict(sector_weights))

        ablations = AblationAnalyzer.evaluate(
            baseline_sharpe=baseline_sharpe,
            baseline_cagr=baseline_cagr,
            ablation_results=dict(ablation_results),
        )

        return RobustnessArtifact(
            candidate_id=candidate.candidate_id,
            top_k_surface=top_k_surface,
            cost_stress=cost_stress,
            concentration=concentration,
            ablations=ablations,
            subperiod_cagr=dict(subperiod_cagr or {}),
        )
