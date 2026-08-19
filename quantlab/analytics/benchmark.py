"""Benchmark performance comparison utilities."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

TRADING_DAYS_PER_YEAR = 252.0


def calculate_beta(asset_returns: Sequence[float], benchmark_returns: Sequence[float]) -> float:
    n = len(asset_returns)
    if n < 2 or len(benchmark_returns) != n:
        return 1.0

    mean_a = sum(asset_returns) / n
    mean_b = sum(benchmark_returns) / n

    cov = sum((asset_returns[i] - mean_a) * (benchmark_returns[i] - mean_b) for i in range(n)) / (
        n - 1
    )
    var_b = sum((benchmark_returns[i] - mean_b) ** 2 for i in range(n)) / (n - 1)

    return cov / var_b if var_b > 1e-8 else 1.0


def calculate_tracking_error(
    asset_returns: Sequence[float], benchmark_returns: Sequence[float]
) -> float:
    n = len(asset_returns)
    if n < 2 or len(benchmark_returns) != n:
        return 0.0

    diffs = [asset_returns[i] - benchmark_returns[i] for i in range(n)]
    mean_diff = sum(diffs) / n
    var_diff = sum((d - mean_diff) ** 2 for d in diffs) / (n - 1)
    return math.sqrt(var_diff) * math.sqrt(TRADING_DAYS_PER_YEAR)


@dataclass(frozen=True, slots=True)
class BenchmarkComparison:
    """What a strategy did relative to the thing it has to beat."""

    benchmark_symbol: str
    sessions: int
    strategy_total_return: float
    benchmark_total_return: float
    strategy_cagr: float
    benchmark_cagr: float
    beta: float
    annualized_alpha: float
    tracking_error: float
    information_ratio: float
    correlation: float

    def as_dict(self) -> dict[str, object]:
        return {
            "benchmark_symbol": self.benchmark_symbol,
            "sessions": self.sessions,
            "strategy_total_return": round(self.strategy_total_return, 6),
            "benchmark_total_return": round(self.benchmark_total_return, 6),
            "strategy_cagr": round(self.strategy_cagr, 6),
            "benchmark_cagr": round(self.benchmark_cagr, 6),
            "beta": round(self.beta, 4),
            "annualized_alpha": round(self.annualized_alpha, 6),
            "tracking_error": round(self.tracking_error, 6),
            "information_ratio": round(self.information_ratio, 4),
            "correlation": round(self.correlation, 4),
        }


def _compound(returns: Sequence[float]) -> float:
    growth = 1.0
    for r in returns:
        growth *= 1.0 + r
    return growth - 1.0


def compare_to_benchmark(
    strategy_returns: Sequence[float],
    benchmark_returns: Sequence[float],
    benchmark_symbol: str,
) -> BenchmarkComparison:
    """Compute beta, Jensen's alpha, tracking error, and information ratio.

    A headline CAGR means nothing on its own: over the same window a strategy with beta
    1.3 to a rising market has to clear 1.3x the market's return before any of it counts
    as skill. Alpha here is the annualized intercept of the strategy against the
    benchmark, not the raw return difference.
    """
    n = min(len(strategy_returns), len(benchmark_returns))
    if n < 2:
        return BenchmarkComparison(benchmark_symbol, n, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0)

    strategy = list(strategy_returns[:n])
    benchmark = list(benchmark_returns[:n])

    beta = calculate_beta(strategy, benchmark)
    mean_strategy = sum(strategy) / n
    mean_benchmark = sum(benchmark) / n
    daily_alpha = mean_strategy - beta * mean_benchmark

    strategy_total = _compound(strategy)
    benchmark_total = _compound(benchmark)
    years = n / TRADING_DAYS_PER_YEAR
    strategy_cagr = (1.0 + strategy_total) ** (1.0 / years) - 1.0 if years > 0 else 0.0
    benchmark_cagr = (1.0 + benchmark_total) ** (1.0 / years) - 1.0 if years > 0 else 0.0

    tracking_error = calculate_tracking_error(strategy, benchmark)
    active = [strategy[i] - benchmark[i] for i in range(n)]
    mean_active = sum(active) / n
    information_ratio = (
        (mean_active * TRADING_DAYS_PER_YEAR) / tracking_error if tracking_error > 1e-9 else 0.0
    )

    var_s = sum((r - mean_strategy) ** 2 for r in strategy)
    var_b = sum((r - mean_benchmark) ** 2 for r in benchmark)
    cov = sum((strategy[i] - mean_strategy) * (benchmark[i] - mean_benchmark) for i in range(n))
    denom = math.sqrt(var_s * var_b)
    correlation = cov / denom if denom > 1e-12 else 0.0

    return BenchmarkComparison(
        benchmark_symbol=benchmark_symbol,
        sessions=n,
        strategy_total_return=strategy_total,
        benchmark_total_return=benchmark_total,
        strategy_cagr=strategy_cagr,
        benchmark_cagr=benchmark_cagr,
        beta=beta,
        annualized_alpha=daily_alpha * TRADING_DAYS_PER_YEAR,
        tracking_error=tracking_error,
        information_ratio=information_ratio,
        correlation=correlation,
    )
