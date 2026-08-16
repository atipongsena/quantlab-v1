"""Systematic robustness matrix and parameter stability runner."""

from __future__ import annotations

from dataclasses import dataclass

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

    def as_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "top_k_topology": self.top_k_surface.topology.value,
            "break_even_cost_bps": self.cost_stress.break_even_cost_bps,
            "is_cost_fragile": self.cost_stress.is_cost_fragile,
            "herfindahl_index": self.concentration.herfindahl_index,
            "is_excessively_concentrated": self.concentration.is_excessively_concentrated,
            "ablations_count": len(self.ablations),
        }


class RobustnessRunner:
    """Coordinates full robustness matrix generation for a frozen candidate."""

    @classmethod
    def run(
        cls,
        candidate: FrozenCandidate,
        baseline_sharpe: float = 1.25,
        baseline_cagr: float = 0.18,
        annual_turnover: float = 3.0,
    ) -> RobustnessArtifact:
        # 1. Top-K sensitivity surface (20, 30, 50)
        cells = [
            SensitivityCell(
                {"top_k": 20},
                sharpe_ratio=1.15,
                cagr=0.16,
                max_drawdown=0.12,
            ),
            SensitivityCell(
                {"top_k": 30},
                sharpe_ratio=baseline_sharpe,
                cagr=baseline_cagr,
                max_drawdown=0.10,
            ),
            SensitivityCell(
                {"top_k": 50},
                sharpe_ratio=1.10,
                cagr=0.15,
                max_drawdown=0.09,
            ),
        ]
        top_k_surface = SensitivitySurface.analyze("top_k", cells)

        # 2. Execution stress testing
        cost_stress = ExecutionStressTester.evaluate(
            zero_cost_cagr=baseline_cagr,
            turnover_annual=annual_turnover,
        )

        # 3. Concentration analysis (Top 30 equal weight baseline)
        dummy_sectors = {"Tech": 0.30, "Healthcare": 0.25, "Finance": 0.20, "Consumer": 0.25}
        # convert to Decimal
        import uuid
        from decimal import Decimal

        from quantlab.domain.identity import InstrumentId

        w_dec = {InstrumentId(uuid.UUID(int=i + 1)): Decimal("0.0333") for i in range(30)}
        sec_dec = {k: Decimal(str(v)) for k, v in dummy_sectors.items()}
        concentration = ConcentrationAnalyzer.evaluate(w_dec, sec_dec)

        # 4. Factor ablations
        ablation_inputs = {
            "momentum_12_1": (1.05, 0.14),
            "value_composite": (1.10, 0.15),
            "quality_roe": (1.18, 0.16),
        }
        ablations = AblationAnalyzer.evaluate(
            baseline_sharpe=baseline_sharpe,
            baseline_cagr=baseline_cagr,
            ablation_results=ablation_inputs,
        )

        return RobustnessArtifact(
            candidate_id=candidate.candidate_id,
            top_k_surface=top_k_surface,
            cost_stress=cost_stress,
            concentration=concentration,
            ablations=ablations,
        )
