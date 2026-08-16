"""Tests for quantile segmentation and returns."""

import uuid

from quantlab.domain.identity import InstrumentId
from quantlab.factors.quantiles import assign_quantiles, compute_quantile_returns


def test_assign_quantiles_uniform() -> None:
    # 10 instruments with scores 1.0 through 10.0
    insts = [InstrumentId(uuid.UUID(int=i + 1)) for i in range(10)]
    scores = {inst: float(i + 1) for i, inst in enumerate(insts)}

    assignments = assign_quantiles(scores, num_quantiles=5)

    # Each quantile should get exactly 2 instruments
    assert len(assignments) == 10
    assert assignments[insts[0]] == 1
    assert assignments[insts[1]] == 1
    assert assignments[insts[8]] == 5
    assert assignments[insts[9]] == 5


def test_compute_quantile_returns() -> None:
    insts = [InstrumentId(uuid.UUID(int=i + 1)) for i in range(10)]
    scores = {inst: float(i + 1) for i, inst in enumerate(insts)}
    quantiles = assign_quantiles(scores, num_quantiles=5)

    # Returns: +10% for high scores, -10% for low scores
    forward_returns = {
        insts[0]: -0.10,
        insts[1]: -0.10,
        insts[2]: -0.05,
        insts[3]: -0.05,
        insts[4]: 0.0,
        insts[5]: 0.0,
        insts[6]: 0.05,
        insts[7]: 0.05,
        insts[8]: 0.10,
        insts[9]: 0.10,
    }

    q_returns = compute_quantile_returns(quantiles, forward_returns, num_quantiles=5)
    assert abs(q_returns[1] - (-0.10)) < 1e-6
    assert abs(q_returns[3] - 0.0) < 1e-6
    assert abs(q_returns[5] - 0.10) < 1e-6
