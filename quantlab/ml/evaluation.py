"""Cross-sectional ranking performance evaluation and metrics."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

# The panel's observation unit is the monthly cross-section, so annualizing an IC series
# uses twelve periods a year. Using 252 here - as if the ICs were daily - inflates every
# information ratio by more than four times.
PERIODS_PER_YEAR = 12.0
QUANTILES = 5


@dataclass(frozen=True, slots=True)
class ModelEvaluationReport:
    model_name: str
    mean_ic: float
    ic_std: float
    ic_ir: float
    ic_ir_annualized: float
    ic_tstat: float
    n_periods: int
    top_bottom_spread: float
    quintile_returns: tuple[float, ...]
    is_monotonic: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "model_name": self.model_name,
            "mean_ic": round(self.mean_ic, 4),
            "ic_std": round(self.ic_std, 4),
            "ic_ir": round(self.ic_ir, 4),
            "ic_ir_annualized": round(self.ic_ir_annualized, 2),
            "ic_tstat": round(self.ic_tstat, 2),
            "n_periods": self.n_periods,
            "top_bottom_spread": round(self.top_bottom_spread, 4),
            "quintile_returns": [round(r, 4) for r in self.quintile_returns],
            "is_monotonic": self.is_monotonic,
        }


def _average_ranks(values: Sequence[float]) -> list[float]:
    """Ranks with ties averaged.

    Assigning tied values the rank of their first occurrence - which is what
    ``sorted(values).index(v)`` does - biases the correlation whenever a model emits
    repeated scores, and tree models emit repeated scores constantly because every leaf
    returns one value.
    """
    n = len(values)
    order = sorted(range(n), key=lambda i: values[i])
    ranks = [0.0] * n
    position = 0
    while position < n:
        end = position
        while end + 1 < n and values[order[end + 1]] == values[order[position]]:
            end += 1
        average = (position + end) / 2.0 + 1.0
        for idx in range(position, end + 1):
            ranks[order[idx]] = average
        position = end + 1
    return ranks


class MLEvaluationEngine:
    """Calculates Spearman rank IC, IR, quantile spreads, and monotonicity."""

    @classmethod
    def compute_spearman_ic(cls, predictions: Sequence[float], targets: Sequence[float]) -> float:
        n = len(predictions)
        if n < 3 or len(targets) != n:
            return 0.0

        rank_p = _average_ranks(predictions)
        rank_t = _average_ranks(targets)

        mean_p = sum(rank_p) / n
        mean_t = sum(rank_t) / n

        cov = sum((rank_p[i] - mean_p) * (rank_t[i] - mean_t) for i in range(n))
        std_p = math.sqrt(sum((v - mean_p) ** 2 for v in rank_p))
        std_t = math.sqrt(sum((v - mean_t) ** 2 for v in rank_t))

        return cov / (std_p * std_t) if (std_p * std_t) > 1e-8 else 0.0

    @classmethod
    def _quintile_returns(
        cls,
        predictions_by_session: Sequence[tuple[Sequence[float], Sequence[float]]],
    ) -> list[float]:
        """Average realized target by predicted quintile, across all test sessions.

        This is the question a portfolio actually asks of a ranking model: if I buy the
        names it likes most and avoid the ones it likes least, what do I get? It has to
        be measured from the predictions and outcomes, not derived from the IC.
        """
        buckets: list[list[float]] = [[] for _ in range(QUANTILES)]

        for preds, targets in predictions_by_session:
            n = len(preds)
            if n < QUANTILES or len(targets) != n:
                continue
            order = sorted(range(n), key=lambda i: preds[i])
            for position, idx in enumerate(order):
                bucket = min(QUANTILES - 1, position * QUANTILES // n)
                buckets[bucket].append(targets[idx])

        return [sum(values) / len(values) if values else 0.0 for values in buckets]

    @classmethod
    def evaluate_model(
        cls,
        model_name: str,
        predictions_by_session: Sequence[tuple[Sequence[float], Sequence[float]]],
        periods_per_year: float = PERIODS_PER_YEAR,
    ) -> ModelEvaluationReport:
        ics: list[float] = []
        for preds, targets in predictions_by_session:
            if len(preds) >= 3:
                ics.append(cls.compute_spearman_ic(preds, targets))

        if not ics:
            return ModelEvaluationReport(
                model_name=model_name,
                mean_ic=0.0,
                ic_std=0.0,
                ic_ir=0.0,
                ic_ir_annualized=0.0,
                ic_tstat=0.0,
                n_periods=0,
                top_bottom_spread=0.0,
                quintile_returns=(0.0,) * QUANTILES,
                is_monotonic=False,
            )

        n_periods = len(ics)
        mean_ic = sum(ics) / n_periods
        var_ic = sum((ic - mean_ic) ** 2 for ic in ics) / (n_periods - 1 if n_periods > 1 else 1)
        std_ic = math.sqrt(var_ic)

        ic_ir = (mean_ic / std_ic) if std_ic > 1e-9 else 0.0
        ic_ir_annualized = ic_ir * math.sqrt(periods_per_year)
        ic_tstat = ic_ir * math.sqrt(n_periods)

        q_rets = cls._quintile_returns(predictions_by_session)
        spread = q_rets[-1] - q_rets[0]
        is_mono = all(q_rets[i] <= q_rets[i + 1] for i in range(len(q_rets) - 1))

        return ModelEvaluationReport(
            model_name=model_name,
            mean_ic=mean_ic,
            ic_std=std_ic,
            ic_ir=ic_ir,
            ic_ir_annualized=ic_ir_annualized,
            ic_tstat=ic_tstat,
            n_periods=n_periods,
            top_bottom_spread=spread,
            quintile_returns=tuple(q_rets),
            is_monotonic=is_mono,
        )
