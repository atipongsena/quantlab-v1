"""Deflated Sharpe Ratio (DSR) calculation correcting for selection bias under multiple testing."""

from __future__ import annotations

import math


def norm_cdf(x: float) -> float:
    """Standard normal cumulative distribution function."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def norm_ppf(p: float) -> float:
    """Approximation of the standard normal inverse CDF (quantile function)."""
    # Rational approximation (Acklam / Abramowitz & Stegun style)
    if p <= 0.0:
        return -8.0
    if p >= 1.0:
        return 8.0
    if p == 0.5:
        return 0.0

    q = p if p < 0.5 else 1.0 - p
    t = math.sqrt(-2.0 * math.log(q))
    # Coefficients
    c0 = 2.515517
    c1 = 0.802853
    c2 = 0.010328
    d1 = 1.432788
    d2 = 0.189269
    d3 = 0.001308

    approx = t - ((c2 * t + c1) * t + c0) / (((d3 * t + d2) * t + d1) * t + 1.0)
    return -approx if p < 0.5 else approx


class DeflatedSharpeCalculator:
    """Computes Deflated Sharpe Ratio p-value correcting for data mining / multiple trials."""

    EULER_MASCHERONI = 0.5772156649015329

    @classmethod
    def expected_max_sharpe(cls, n_trials: int, variance_trials: float = 0.25) -> float:
        """Estimates expected maximum Sharpe ratio under null hypothesis across N trials."""
        if n_trials <= 1:
            return 0.0

        std_trials = math.sqrt(variance_trials)
        gamma = cls.EULER_MASCHERONI

        # Expected maximum of N standard normal variables
        z1 = norm_ppf(1.0 - 1.0 / n_trials)
        z2 = norm_ppf(1.0 - 1.0 / (n_trials * math.e))
        e_max_z = (1.0 - gamma) * z1 + gamma * z2

        return e_max_z * std_trials

    @classmethod
    def calculate(
        cls,
        observed_sharpe: float,
        n_trials: int,
        variance_trials: float = 0.25,
        skewness: float = 0.0,
        kurtosis: float = 3.0,
        sample_length: int = 252,
    ) -> float:
        """Calculates DSR p-value (probability of observed Sharpe exceeding max null)."""
        if sample_length < 5 or n_trials < 1:
            return 0.5

        # Standard error of Sharpe ratio with skewness and kurtosis
        sr = observed_sharpe
        t = sample_length
        denom_term = 1.0 - (skewness * sr) + ((kurtosis - 1.0) / 4.0) * (sr**2)
        if denom_term < 1e-6:
            denom_term = 1e-6

        se_sr = math.sqrt(denom_term / float(t - 1))

        # Expected max Sharpe under N null trials
        exp_max_sr = cls.expected_max_sharpe(n_trials, variance_trials)

        # Compute z-statistic and DSR probability
        z_stat = (sr - exp_max_sr) / se_sr if se_sr > 1e-8 else 0.0
        return norm_cdf(z_stat)
