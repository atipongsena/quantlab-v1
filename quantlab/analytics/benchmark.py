"""Benchmark performance comparison utilities."""

from __future__ import annotations

import math
from collections.abc import Sequence


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
    return math.sqrt(var_diff) * math.sqrt(252.0)
