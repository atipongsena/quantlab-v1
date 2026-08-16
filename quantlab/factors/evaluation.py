"""Factor research analytics, IC evaluation, decay profiles, and diagnostic spreads."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date

from quantlab.common.hashing import canonical_hash
from quantlab.domain.identity import InstrumentId
from quantlab.factors.contracts import FactorSnapshot
from quantlab.factors.quantiles import assign_quantiles, compute_quantile_returns
from quantlab.factors.transforms import rank_cross_section


@dataclass(frozen=True, slots=True)
class ForwardReturnView:
    """Historical forward returns indexed by (session, horizon_sessions)."""

    returns: Mapping[tuple[date, int], Mapping[InstrumentId, float]]

    def get_returns(
        self,
        session: date,
        horizon_sessions: int = 21,
    ) -> Mapping[InstrumentId, float]:
        return self.returns.get((session, horizon_sessions), {})


@dataclass(frozen=True, slots=True)
class EvaluationSpec:
    primary_horizon: int = 21
    decay_horizons: tuple[int, ...] = (21, 63, 126, 252)
    num_quantiles: int = 5
    annualization_factor: float = 12.0


@dataclass(frozen=True, slots=True)
class FactorResearchResult:
    factor_id: str
    start_session: date
    end_session: date
    num_sessions: int
    ic_mean: float
    ic_std: float
    ic_ir: float
    ic_positive_pct: float
    rank_ic_mean: float
    rank_ic_std: float
    rank_ic_ir: float
    decay_profile: Mapping[str, float]
    quantile_returns: Mapping[str, float]
    spread_q5_minus_q1: float
    coverage_mean: float
    turnover_mean: float
    diagnostic_label: str = "DIAGNOSTIC_ONLY_NON_DEPLOYABLE"
    metadata: Mapping[str, object] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return {
            "factor_id": self.factor_id,
            "start_session": self.start_session.isoformat(),
            "end_session": self.end_session.isoformat(),
            "num_sessions": self.num_sessions,
            "ic_mean": round(self.ic_mean, 6),
            "ic_std": round(self.ic_std, 6),
            "ic_ir": round(self.ic_ir, 6),
            "ic_positive_pct": round(self.ic_positive_pct, 4),
            "rank_ic_mean": round(self.rank_ic_mean, 6),
            "rank_ic_std": round(self.rank_ic_std, 6),
            "rank_ic_ir": round(self.rank_ic_ir, 6),
            "decay_profile": {k: round(v, 6) for k, v in self.decay_profile.items()},
            "quantile_returns": {k: round(v, 6) for k, v in self.quantile_returns.items()},
            "spread_q5_minus_q1": round(self.spread_q5_minus_q1, 6),
            "coverage_mean": round(self.coverage_mean, 4),
            "turnover_mean": round(self.turnover_mean, 4),
            "diagnostic_label": self.diagnostic_label,
            "metadata": dict(self.metadata),
        }

    @property
    def content_hash(self) -> str:
        return canonical_hash(self.as_dict())


def _pearson_correlation(
    x_map: Mapping[InstrumentId, float],
    y_map: Mapping[InstrumentId, float],
) -> float | None:
    common_keys = sorted(set(x_map.keys()) & set(y_map.keys()), key=lambda item: str(item.value))
    n = len(common_keys)
    if n < 3:
        return None

    xs = [x_map[k] for k in common_keys]
    ys = [y_map[k] for k in common_keys]

    mean_x = sum(xs) / n
    mean_y = sum(ys) / n

    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)

    if var_x < 1e-12 or var_y < 1e-12:
        return 0.0

    cov_xy = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(n))
    denom = math.sqrt(var_x * var_y)
    return cov_xy / denom if denom > 1e-12 else 0.0


def _spearman_rank_correlation(
    x_map: Mapping[InstrumentId, float],
    y_map: Mapping[InstrumentId, float],
) -> float | None:
    common_keys = sorted(set(x_map.keys()) & set(y_map.keys()), key=lambda item: str(item.value))
    if len(common_keys) < 3:
        return None

    x_sub = {k: x_map[k] for k in common_keys}
    y_sub = {k: y_map[k] for k in common_keys}

    rx = rank_cross_section(x_sub, normalize=True)
    ry = rank_cross_section(y_sub, normalize=True)

    return _pearson_correlation(rx, ry)


class FactorEvaluator:
    """Evaluates cross-sectional factors against forward returns."""

    def __init__(self, spec: EvaluationSpec | None = None) -> None:
        self._spec = spec or EvaluationSpec()

    def evaluate(
        self,
        snapshots: Sequence[FactorSnapshot],
        forward_returns: ForwardReturnView,
    ) -> FactorResearchResult:
        if not snapshots:
            raise ValueError("Snapshots sequence cannot be empty for evaluation")

        sorted_snaps = sorted(snapshots, key=lambda s: s.session)
        factor_id = sorted_snaps[0].factor_id
        start_session = sorted_snaps[0].session
        end_session = sorted_snaps[-1].session
        num_sessions = len(sorted_snaps)

        ic_series: list[float] = []
        rank_ic_series: list[float] = []
        coverages: list[float] = []
        turnovers: list[float] = []

        # Quantile returns cumulative collectors
        quantile_sums: dict[int, list[float]] = {
            q: [] for q in range(1, self._spec.num_quantiles + 1)
        }

        prev_scores: dict[InstrumentId, float] | None = None

        for snap in sorted_snaps:
            valid_scores = snap.valid_scores()
            total_universe = len(snap.values)
            coverage = (len(valid_scores) / total_universe) if total_universe > 0 else 0.0
            coverages.append(coverage)

            # Turnover against prior session
            if prev_scores is not None and prev_scores and valid_scores:
                rank_curr = rank_cross_section(valid_scores, normalize=True)
                rank_prev = rank_cross_section(prev_scores, normalize=True)
                corr = _pearson_correlation(rank_curr, rank_prev)
                # Turnover is 1 - rank correlation (bounded [0, 2])
                turnover = 1.0 - (corr if corr is not None else 0.0)
                turnovers.append(max(0.0, turnover))
            prev_scores = valid_scores

            # Forward returns for primary horizon
            fwd_ret = forward_returns.get_returns(snap.session, self._spec.primary_horizon)
            if fwd_ret and valid_scores:
                ic_val = _pearson_correlation(valid_scores, fwd_ret)
                if ic_val is not None:
                    ic_series.append(ic_val)

                ric_val = _spearman_rank_correlation(valid_scores, fwd_ret)
                if ric_val is not None:
                    rank_ic_series.append(ric_val)

                # Quantiles
                q_assign = assign_quantiles(valid_scores, self._spec.num_quantiles)
                q_rets = compute_quantile_returns(q_assign, fwd_ret, self._spec.num_quantiles)
                for q, ret in q_rets.items():
                    quantile_sums[q].append(ret)

        # Compute summary stats
        n_ic = len(ic_series)
        ic_mean = sum(ic_series) / n_ic if n_ic > 0 else 0.0
        ic_std = (
            math.sqrt(sum((x - ic_mean) ** 2 for x in ic_series) / max(1, n_ic - 1))
            if n_ic > 1
            else 0.0
        )
        ic_ir = (
            (ic_mean / ic_std) * math.sqrt(self._spec.annualization_factor)
            if ic_std > 1e-6
            else 0.0
        )
        ic_pos_pct = (sum(1 for x in ic_series if x > 0) / n_ic) if n_ic > 0 else 0.0

        n_ric = len(rank_ic_series)
        rank_ic_mean = sum(rank_ic_series) / n_ric if n_ric > 0 else 0.0
        rank_ic_std = (
            math.sqrt(sum((x - rank_ic_mean) ** 2 for x in rank_ic_series) / max(1, n_ric - 1))
            if n_ric > 1
            else 0.0
        )
        rank_ic_ir = (
            (rank_ic_mean / rank_ic_std) * math.sqrt(self._spec.annualization_factor)
            if rank_ic_std > 1e-6
            else 0.0
        )

        # Decay profile over horizons (1M=21, 3M=63, 6M=126, 12M=252)
        horizon_labels = {21: "1M", 63: "3M", 126: "6M", 252: "12M"}
        decay_profile: dict[str, float] = {}
        for h in self._spec.decay_horizons:
            label = horizon_labels.get(h, f"{h}D")
            h_ics: list[float] = []
            for snap in sorted_snaps:
                h_fwd = forward_returns.get_returns(snap.session, h)
                v_scores = snap.valid_scores()
                if h_fwd and v_scores:
                    val = _spearman_rank_correlation(v_scores, h_fwd)
                    if val is not None:
                        h_ics.append(val)
            decay_profile[label] = sum(h_ics) / len(h_ics) if h_ics else 0.0

        # Mean annualized quantile returns
        ann_q_rets: dict[str, float] = {}
        for q in range(1, self._spec.num_quantiles + 1):
            q_list = quantile_sums.get(q, [])
            mean_q = sum(q_list) / len(q_list) if q_list else 0.0
            ann_q_rets[f"Q{q}"] = mean_q * self._spec.annualization_factor

        q1_ret = ann_q_rets.get("Q1", 0.0)
        q5_ret = ann_q_rets.get(f"Q{self._spec.num_quantiles}", 0.0)
        spread = q5_ret - q1_ret

        coverage_mean = sum(coverages) / len(coverages) if coverages else 0.0
        turnover_mean = sum(turnovers) / len(turnovers) if turnovers else 0.0

        return FactorResearchResult(
            factor_id=factor_id,
            start_session=start_session,
            end_session=end_session,
            num_sessions=num_sessions,
            ic_mean=ic_mean,
            ic_std=ic_std,
            ic_ir=ic_ir,
            ic_positive_pct=ic_pos_pct,
            rank_ic_mean=rank_ic_mean,
            rank_ic_std=rank_ic_std,
            rank_ic_ir=rank_ic_ir,
            decay_profile=decay_profile,
            quantile_returns=ann_q_rets,
            spread_q5_minus_q1=spread,
            coverage_mean=coverage_mean,
            turnover_mean=turnover_mean,
        )
