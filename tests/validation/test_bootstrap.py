"""Tests for stationary block bootstrap."""

import math

from quantlab.validation.bootstrap import BootstrapRunner, BootstrapSpec


def test_stationary_block_bootstrap_confidence_interval() -> None:
    # 252 daily returns of 0.05% (~12.6% annual return) with 1% daily vol
    returns = [0.0005 + 0.01 * math.sin(i * 0.1) for i in range(252)]

    spec = BootstrapSpec(block_length=21, simulations=200, confidence_level=0.95)
    dist = BootstrapRunner.run(returns, spec, seed=42)

    assert dist.point_estimate != 0.0
    assert dist.ci_lower < dist.ci_upper
    assert dist.ci_lower <= dist.point_estimate <= dist.ci_upper
    assert len(dist.simulated_values) == 200
