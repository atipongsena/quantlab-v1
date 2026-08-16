"""Dependence-aware stationary block bootstrap and confidence interval estimation."""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BootstrapSpec:
    method: str = "stationary_block"
    block_length: int = 21
    simulations: int = 1000
    confidence_level: float = 0.95


@dataclass(frozen=True, slots=True)
class BootstrapDistribution:
    metric_name: str
    point_estimate: float
    ci_lower: float
    ci_upper: float
    standard_error: float
    simulated_values: tuple[float, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "metric_name": self.metric_name,
            "point_estimate": round(self.point_estimate, 4),
            "ci_lower": round(self.ci_lower, 4),
            "ci_upper": round(self.ci_upper, 4),
            "standard_error": round(self.standard_error, 4),
        }


class BootstrapRunner:
    """Performs stationary block bootstrap preserving autocorrelation."""

    @classmethod
    def run(
        cls,
        returns: Sequence[float],
        spec: BootstrapSpec | None = None,
        seed: int = 42,
    ) -> BootstrapDistribution:
        bs_spec = spec or BootstrapSpec()
        n = len(returns)
        if n < 5:
            # Fallback for minimal series
            pt = (sum(returns) / n * math.sqrt(252.0)) if n > 0 else 0.0
            return BootstrapDistribution(
                metric_name="annualized_sharpe",
                point_estimate=pt,
                ci_lower=pt,
                ci_upper=pt,
                standard_error=0.0,
                simulated_values=(pt,),
            )

        rng = random.Random(seed)
        p = 1.0 / float(bs_spec.block_length) if bs_spec.block_length > 0 else 1.0

        # Compute point estimate
        mean_ret = sum(returns) / n
        std_ret = math.sqrt(sum((r - mean_ret) ** 2 for r in returns) / (n - 1))
        point_estimate = (mean_ret / std_ret * math.sqrt(252.0)) if std_ret > 1e-8 else 0.0

        sim_sharpes: list[float] = []
        for _ in range(bs_spec.simulations):
            # Stationary block resampling
            sample: list[float] = []
            idx = rng.randint(0, n - 1)
            while len(sample) < n:
                sample.append(returns[idx])
                if rng.random() < p:
                    idx = rng.randint(0, n - 1)
                else:
                    idx = (idx + 1) % n

            s_mean = sum(sample) / n
            s_var = sum((r - s_mean) ** 2 for r in sample) / (n - 1)
            s_std = math.sqrt(s_var)
            s_sharpe = (s_mean / s_std * math.sqrt(252.0)) if s_std > 1e-8 else 0.0
            sim_sharpes.append(s_sharpe)

        sorted_sharpes = sorted(sim_sharpes)
        alpha = 1.0 - bs_spec.confidence_level
        lower_idx = max(0, int((alpha / 2.0) * len(sorted_sharpes)))
        upper_idx = min(len(sorted_sharpes) - 1, int((1.0 - alpha / 2.0) * len(sorted_sharpes)))

        ci_lower = sorted_sharpes[lower_idx]
        ci_upper = sorted_sharpes[upper_idx]

        sim_mean = sum(sim_sharpes) / len(sim_sharpes)
        se = math.sqrt(sum((s - sim_mean) ** 2 for s in sim_sharpes) / len(sim_sharpes))

        return BootstrapDistribution(
            metric_name="annualized_sharpe",
            point_estimate=point_estimate,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            standard_error=se,
            simulated_values=tuple(sorted_sharpes),
        )
