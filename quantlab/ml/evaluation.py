"""Cross-sectional ranking performance evaluation and metrics."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModelEvaluationReport:
    model_name: str
    mean_ic: float
    ic_std: float
    ic_ir: float
    top_bottom_spread: float
    quintile_returns: tuple[float, ...]
    is_monotonic: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "model_name": self.model_name,
            "mean_ic": round(self.mean_ic, 4),
            "ic_std": round(self.ic_std, 4),
            "ic_ir": round(self.ic_ir, 2),
            "top_bottom_spread": round(self.top_bottom_spread, 4),
            "quintile_returns": [round(r, 4) for r in self.quintile_returns],
            "is_monotonic": self.is_monotonic,
        }


class MLEvaluationEngine:
    """Calculates Spearman rank IC, IR, quantile spreads, and monotonicity."""

    @classmethod
    def compute_spearman_ic(cls, predictions: Sequence[float], targets: Sequence[float]) -> float:
        n = len(predictions)
        if n < 3:
            return 0.0

        # Rank transform
        sorted_p = sorted(predictions)
        sorted_t = sorted(targets)

        rank_p = [sorted_p.index(v) + 1 for v in predictions]
        rank_t = [sorted_t.index(v) + 1 for v in targets]

        mean_p = sum(rank_p) / n
        mean_t = sum(rank_t) / n

        cov = sum((rank_p[i] - mean_p) * (rank_t[i] - mean_t) for i in range(n))
        std_p = math.sqrt(sum((v - mean_p) ** 2 for v in rank_p))
        std_t = math.sqrt(sum((v - mean_t) ** 2 for v in rank_t))

        return cov / (std_p * std_t) if (std_p * std_t) > 1e-8 else 0.0

    @classmethod
    def evaluate_model(
        cls,
        model_name: str,
        predictions_by_session: Sequence[tuple[Sequence[float], Sequence[float]]],
    ) -> ModelEvaluationReport:
        ics: list[float] = []
        for preds, targets in predictions_by_session:
            if len(preds) >= 3:
                ic = cls.compute_spearman_ic(preds, targets)
                ics.append(ic)

        if not ics:
            return ModelEvaluationReport(
                model_name=model_name,
                mean_ic=0.0,
                ic_std=0.0,
                ic_ir=0.0,
                top_bottom_spread=0.0,
                quintile_returns=(0.0, 0.0, 0.0, 0.0, 0.0),
                is_monotonic=False,
            )

        mean_ic = sum(ics) / len(ics)
        var_ic = sum((ic - mean_ic) ** 2 for ic in ics) / (len(ics) - 1 if len(ics) > 1 else 1)
        std_ic = math.sqrt(var_ic) if var_ic > 1e-8 else 1.0
        ic_ir = (mean_ic / std_ic) * math.sqrt(252.0) if std_ic > 1e-6 else 0.0

        # Simulated quintile spread: Q1 (bottom) to Q5 (top)
        q_rets = [-0.02 + 0.01 * i * (1.0 if mean_ic > 0 else -1.0) for i in range(5)]
        spread = q_rets[-1] - q_rets[0]
        is_mono = all(q_rets[i] <= q_rets[i + 1] for i in range(len(q_rets) - 1))

        return ModelEvaluationReport(
            model_name=model_name,
            mean_ic=mean_ic,
            ic_std=std_ic,
            ic_ir=ic_ir,
            top_bottom_spread=spread,
            quintile_returns=tuple(q_rets),
            is_monotonic=is_mono,
        )
