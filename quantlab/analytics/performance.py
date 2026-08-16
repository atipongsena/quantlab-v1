"""Authoritative portfolio performance and risk metrics calculations."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class PerformanceMetrics:
    total_return: float
    cagr: float
    annualized_volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    max_drawdown_duration_days: int
    calmar_ratio: float
    win_rate: float
    profit_factor: float
    total_turnover: float
    total_fees: float
    total_slippage: float
    benchmark_total_return: float | None = None
    alpha: float | None = None
    beta: float | None = None
    information_ratio: float | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "total_return": round(self.total_return, 6),
            "cagr": round(self.cagr, 6),
            "annualized_volatility": round(self.annualized_volatility, 6),
            "sharpe_ratio": round(self.sharpe_ratio, 4),
            "sortino_ratio": round(self.sortino_ratio, 4),
            "max_drawdown": round(self.max_drawdown, 6),
            "max_drawdown_duration_days": self.max_drawdown_duration_days,
            "calmar_ratio": round(self.calmar_ratio, 4),
            "win_rate": round(self.win_rate, 4),
            "profit_factor": round(self.profit_factor, 4),
            "total_turnover": round(self.total_turnover, 4),
            "total_fees": round(self.total_fees, 2),
            "total_slippage": round(self.total_slippage, 2),
            "benchmark_total_return": round(self.benchmark_total_return, 6)
            if self.benchmark_total_return is not None
            else None,
            "alpha": round(self.alpha, 6) if self.alpha is not None else None,
            "beta": round(self.beta, 4) if self.beta is not None else None,
            "information_ratio": round(self.information_ratio, 4)
            if self.information_ratio is not None
            else None,
        }


class PerformanceCalculator:
    """Calculates comprehensive portfolio performance statistics."""

    @classmethod
    def calculate(
        cls,
        equity_series: Sequence[Decimal],
        risk_free_rate: float = 0.0,
        total_turnover: Decimal = Decimal("0.0"),
        total_fees: Decimal = Decimal("0.0"),
        total_slippage: Decimal = Decimal("0.0"),
        benchmark_returns: Sequence[float] | None = None,
    ) -> PerformanceMetrics:
        if len(equity_series) < 2:
            return PerformanceMetrics(
                total_return=0.0,
                cagr=0.0,
                annualized_volatility=0.0,
                sharpe_ratio=0.0,
                sortino_ratio=0.0,
                max_drawdown=0.0,
                max_drawdown_duration_days=0,
                calmar_ratio=0.0,
                win_rate=0.0,
                profit_factor=0.0,
                total_turnover=float(total_turnover),
                total_fees=float(total_fees),
                total_slippage=float(total_slippage),
            )

        eq_floats = [float(e) for e in equity_series]
        initial_equity = eq_floats[0]
        final_equity = eq_floats[-1]
        total_return = (
            (final_equity - initial_equity) / initial_equity if initial_equity > 0 else 0.0
        )

        # Daily returns
        daily_returns: list[float] = []
        for i in range(1, len(eq_floats)):
            prev = eq_floats[i - 1]
            cur = eq_floats[i]
            daily_returns.append((cur - prev) / prev if prev > 0 else 0.0)

        n_sessions = len(daily_returns)
        years = n_sessions / 252.0 if n_sessions > 0 else 1.0

        # CAGR
        if total_return > -1.0 and years > 0:
            cagr = (1.0 + total_return) ** (1.0 / years) - 1.0
        else:
            cagr = -1.0

        # Volatility
        mean_ret = sum(daily_returns) / n_sessions if n_sessions > 0 else 0.0
        variance = (
            sum((r - mean_ret) ** 2 for r in daily_returns) / (n_sessions - 1)
            if n_sessions > 1
            else 0.0
        )
        std_ret = math.sqrt(variance)
        ann_vol = std_ret * math.sqrt(252.0)

        # Sharpe ratio
        sharpe = (cagr - risk_free_rate) / ann_vol if ann_vol > 1e-8 else 0.0

        # Downside deviation & Sortino ratio
        downside_diffs = [min(0.0, r - (risk_free_rate / 252.0)) for r in daily_returns]
        downside_var = (
            sum(d**2 for d in downside_diffs) / (n_sessions - 1) if n_sessions > 1 else 0.0
        )
        downside_std = math.sqrt(downside_var) * math.sqrt(252.0)
        sortino = (cagr - risk_free_rate) / downside_std if downside_std > 1e-8 else 0.0

        # Max Drawdown & duration
        peak = eq_floats[0]
        max_dd = 0.0
        max_dd_duration = 0
        current_dd_duration = 0

        for eq in eq_floats:
            if eq > peak:
                peak = eq
                current_dd_duration = 0
            else:
                dd = (peak - eq) / peak if peak > 0 else 0.0
                if dd > max_dd:
                    max_dd = dd
                current_dd_duration += 1
                if current_dd_duration > max_dd_duration:
                    max_dd_duration = current_dd_duration

        calmar = cagr / max_dd if max_dd > 1e-8 else 0.0

        # Win rate and profit factor
        wins = [r for r in daily_returns if r > 0]
        losses = [r for r in daily_returns if r < 0]
        win_rate = len(wins) / n_sessions if n_sessions > 0 else 0.0
        sum_wins = sum(wins)
        sum_losses = abs(sum(losses))
        profit_factor = (
            (sum_wins / sum_losses) if sum_losses > 1e-8 else (99.0 if sum_wins > 0 else 0.0)
        )

        # Benchmark excess metrics
        alpha = None
        beta = None
        info_ratio = None
        bm_total_ret = None

        if benchmark_returns and len(benchmark_returns) == len(daily_returns):
            bm_total_ret = math.prod(1.0 + r for r in benchmark_returns) - 1.0
            bm_mean = sum(benchmark_returns) / n_sessions
            cov = (
                sum(
                    (daily_returns[i] - mean_ret) * (benchmark_returns[i] - bm_mean)
                    for i in range(n_sessions)
                )
                / (n_sessions - 1)
                if n_sessions > 1
                else 0.0
            )
            bm_var = (
                sum((r - bm_mean) ** 2 for r in benchmark_returns) / (n_sessions - 1)
                if n_sessions > 1
                else 0.0
            )
            beta = cov / bm_var if bm_var > 1e-8 else 1.0
            bm_cagr = (
                (1.0 + bm_total_ret) ** (1.0 / years) - 1.0
                if (bm_total_ret > -1.0 and years > 0)
                else -1.0
            )
            tracking_diffs = [daily_returns[i] - benchmark_returns[i] for i in range(n_sessions)]
            track_err = (
                math.sqrt(sum(td**2 for td in tracking_diffs) / (n_sessions - 1)) * math.sqrt(252.0)
                if n_sessions > 1
                else 0.0
            )
            info_ratio = (cagr - bm_cagr) / track_err if track_err > 1e-8 else 0.0

        return PerformanceMetrics(
            total_return=total_return,
            cagr=cagr,
            annualized_volatility=ann_vol,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            max_drawdown=max_dd,
            max_drawdown_duration_days=max_dd_duration,
            calmar_ratio=calmar,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_turnover=float(total_turnover),
            total_fees=float(total_fees),
            total_slippage=float(total_slippage),
            benchmark_total_return=bm_total_ret,
            alpha=alpha,
            beta=beta,
            information_ratio=info_ratio,
        )
