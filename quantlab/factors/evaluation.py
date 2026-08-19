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
    newey_west_lags: int = 3


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _sample_std(values: Sequence[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    mu = _mean(values)
    return math.sqrt(sum((v - mu) ** 2 for v in values) / (n - 1))


def newey_west_tstat(series: Sequence[float], lags: int = 3) -> float:
    """t-statistic for the mean of a serially correlated series.

    Overlapping forward-return windows make consecutive ICs correlated, so the plain
    OLS t-statistic overstates significance. Newey-West widens the standard error by the
    autocovariance the overlap induces (Bartlett kernel), which is the correction a quant
    reviewer expects to see on any IC or factor-return t-stat.
    """
    n = len(series)
    if n < 3:
        return 0.0

    mu = _mean(series)
    demeaned = [v - mu for v in series]

    gamma0 = sum(d * d for d in demeaned) / n
    variance = gamma0
    usable_lags = min(lags, n - 1)
    for lag in range(1, usable_lags + 1):
        gamma = sum(demeaned[t] * demeaned[t - lag] for t in range(lag, n)) / n
        weight = 1.0 - lag / (usable_lags + 1.0)
        variance += 2.0 * weight * gamma

    if variance <= 1e-18:
        return 0.0
    return mu / math.sqrt(variance / n)


def _annualize_compound(period_returns: Sequence[float], periods_per_year: float) -> float:
    """Geometric annualized return of a period-return series.

    Multiplying a mean monthly return by 12 inflates a lucky month into a headline
    number; compounding the realized path and annualizing over elapsed time does not.
    """
    if not period_returns:
        return 0.0
    growth = 1.0
    for r in period_returns:
        growth *= 1.0 + r
    if growth <= 0.0:
        return -1.0
    years = len(period_returns) / periods_per_year
    if years <= 0.0:
        return 0.0
    return float(growth ** (1.0 / years)) - 1.0


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
    rank_ic_tstat: float = 0.0
    rank_ic_tstat_newey_west: float = 0.0
    breadth_mean: float = 0.0
    quantile_monotonicity: float = 0.0
    long_short_ann_return: float = 0.0
    long_short_ann_vol: float = 0.0
    long_short_sharpe: float = 0.0
    subperiod_rank_ic: Mapping[str, float] = field(default_factory=dict)
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
            "rank_ic_tstat": round(self.rank_ic_tstat, 4),
            "rank_ic_tstat_newey_west": round(self.rank_ic_tstat_newey_west, 4),
            "breadth_mean": round(self.breadth_mean, 2),
            "decay_profile": {k: round(v, 6) for k, v in self.decay_profile.items()},
            "quantile_returns": {k: round(v, 6) for k, v in self.quantile_returns.items()},
            "quantile_monotonicity": round(self.quantile_monotonicity, 4),
            "spread_q5_minus_q1": round(self.spread_q5_minus_q1, 6),
            "long_short_ann_return": round(self.long_short_ann_return, 6),
            "long_short_ann_vol": round(self.long_short_ann_vol, 6),
            "long_short_sharpe": round(self.long_short_sharpe, 4),
            "subperiod_rank_ic": {k: round(v, 6) for k, v in self.subperiod_rank_ic.items()},
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


def _rank_correlation_of_sequence(values: Sequence[float]) -> float:
    """Spearman correlation between a sequence's position and its value.

    Returns +1 when returns rise strictly with quantile index and -1 when they fall.
    """
    n = len(values)
    if n < 2:
        return 0.0

    order = sorted(range(n), key=lambda i: values[i])
    ranks = [0.0] * n
    for rank_pos, idx in enumerate(order):
        ranks[idx] = float(rank_pos)

    positions = [float(i) for i in range(n)]
    mean_pos = _mean(positions)
    mean_rank = _mean(ranks)

    cov = sum((positions[i] - mean_pos) * (ranks[i] - mean_rank) for i in range(n))
    var_pos = sum((p - mean_pos) ** 2 for p in positions)
    var_rank = sum((r - mean_rank) ** 2 for r in ranks)
    denom = math.sqrt(var_pos * var_rank)
    return cov / denom if denom > 1e-12 else 0.0


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
        rank_ic_by_year: dict[int, list[float]] = {}
        coverages: list[float] = []
        turnovers: list[float] = []
        breadths: list[int] = []

        # Quantile returns cumulative collectors
        quantile_sums: dict[int, list[float]] = {
            q: [] for q in range(1, self._spec.num_quantiles + 1)
        }
        long_short_series: list[float] = []

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
                    rank_ic_by_year.setdefault(snap.session.year, []).append(ric_val)

                breadths.append(len(set(valid_scores) & set(fwd_ret)))

                # Quantiles
                q_assign = assign_quantiles(valid_scores, self._spec.num_quantiles)
                q_rets = compute_quantile_returns(q_assign, fwd_ret, self._spec.num_quantiles)
                for q, ret in q_rets.items():
                    quantile_sums[q].append(ret)

                top_q = self._spec.num_quantiles
                if top_q in q_rets and 1 in q_rets:
                    long_short_series.append(q_rets[top_q] - q_rets[1])

        # Compute summary stats. IR is the per-rebalance ratio mean(IC)/std(IC); the
        # annualized figure is IR * sqrt(periods_per_year) and is reported separately so
        # the two are never conflated when a t-statistic is derived downstream.
        n_ic = len(ic_series)
        ic_mean = _mean(ic_series)
        ic_std = _sample_std(ic_series)
        ic_ir = (ic_mean / ic_std) if ic_std > 1e-9 else 0.0
        ic_pos_pct = (sum(1 for x in ic_series if x > 0) / n_ic) if n_ic > 0 else 0.0

        n_ric = len(rank_ic_series)
        rank_ic_mean = _mean(rank_ic_series)
        rank_ic_std = _sample_std(rank_ic_series)
        rank_ic_ir = (rank_ic_mean / rank_ic_std) if rank_ic_std > 1e-9 else 0.0
        rank_ic_tstat = rank_ic_ir * math.sqrt(n_ric) if n_ric > 0 else 0.0
        rank_ic_tstat_nw = newey_west_tstat(rank_ic_series, self._spec.newey_west_lags)

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

        # Quantile portfolio returns, compounded then annualized over elapsed time.
        periods_per_year = self._spec.annualization_factor
        ann_q_rets: dict[str, float] = {}
        for q in range(1, self._spec.num_quantiles + 1):
            ann_q_rets[f"Q{q}"] = _annualize_compound(quantile_sums.get(q, []), periods_per_year)

        q1_ret = ann_q_rets.get("Q1", 0.0)
        q5_ret = ann_q_rets.get(f"Q{self._spec.num_quantiles}", 0.0)
        spread = q5_ret - q1_ret

        # Monotonicity: rank correlation between quantile index and realized return.
        # A factor whose middle buckets are scrambled is not a usable sort even when the
        # extreme buckets happen to line up.
        ordered_q = [ann_q_rets[f"Q{q}"] for q in range(1, self._spec.num_quantiles + 1)]
        monotonicity = _rank_correlation_of_sequence(ordered_q)

        ls_ann_return = _annualize_compound(long_short_series, periods_per_year)
        ls_ann_vol = _sample_std(long_short_series) * math.sqrt(periods_per_year)
        ls_sharpe = (ls_ann_return / ls_ann_vol) if ls_ann_vol > 1e-9 else 0.0

        subperiod_rank_ic = {
            str(year): _mean(values) for year, values in sorted(rank_ic_by_year.items())
        }

        coverage_mean = _mean(coverages)
        turnover_mean = _mean(turnovers)
        breadth_mean = _mean([float(b) for b in breadths])

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
            rank_ic_tstat=rank_ic_tstat,
            rank_ic_tstat_newey_west=rank_ic_tstat_nw,
            breadth_mean=breadth_mean,
            quantile_monotonicity=monotonicity,
            long_short_ann_return=ls_ann_return,
            long_short_ann_vol=ls_ann_vol,
            long_short_sharpe=ls_sharpe,
            subperiod_rank_ic=subperiod_rank_ic,
        )
