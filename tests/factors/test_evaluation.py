"""Tests for factor research and evaluation engine."""

import uuid
from datetime import UTC, date, datetime

from quantlab.domain.identity import InstrumentId
from quantlab.factors.contracts import FactorSnapshot, FactorValue
from quantlab.factors.evaluation import (
    EvaluationSpec,
    FactorEvaluator,
    ForwardReturnView,
)


def test_factor_evaluator_metrics() -> None:
    session1 = date(2020, 1, 31)
    session2 = date(2020, 2, 28)
    as_of = datetime(2020, 3, 1, 16, 0, tzinfo=UTC)

    # 10 instruments
    universe = [InstrumentId(uuid.UUID(int=i + 1)) for i in range(10)]

    # Perfect correlation with forward returns: scores = [1..10], fwd returns = [0.01..0.10]
    scores1 = {u: float(i + 1) for i, u in enumerate(universe)}
    fwd_ret1 = {u: 0.01 * (i + 1) for i, u in enumerate(universe)}

    # Slightly noisy correlation for session 2
    scores2 = {u: float(i + 1) for i, u in enumerate(universe)}
    fwd_ret2 = {u: 0.01 * (i + 1) + 0.002 for i, u in enumerate(universe)}

    snap1 = FactorSnapshot(
        factor_id="test_factor",
        version="v1",
        session=session1,
        as_of=as_of,
        values={
            u: FactorValue(instrument_id=u, value=scores1[u], missing_reason=None) for u in universe
        },
        content_hash="hash1",
    )
    snap2 = FactorSnapshot(
        factor_id="test_factor",
        version="v1",
        session=session2,
        as_of=as_of,
        values={
            u: FactorValue(instrument_id=u, value=scores2[u], missing_reason=None) for u in universe
        },
        content_hash="hash2",
    )

    forward_returns = ForwardReturnView(
        returns={
            (session1, 21): fwd_ret1,
            (session1, 63): fwd_ret1,
            (session1, 126): fwd_ret1,
            (session1, 252): fwd_ret1,
            (session2, 21): fwd_ret2,
            (session2, 63): fwd_ret2,
            (session2, 126): fwd_ret2,
            (session2, 252): fwd_ret2,
        }
    )

    evaluator = FactorEvaluator(EvaluationSpec(num_quantiles=5))
    result = evaluator.evaluate([snap1, snap2], forward_returns)

    assert result.factor_id == "test_factor"
    assert result.num_sessions == 2
    assert result.ic_mean > 0.99
    assert result.rank_ic_mean > 0.99
    assert result.ic_positive_pct == 1.0
    assert result.diagnostic_label == "DIAGNOSTIC_ONLY_NON_DEPLOYABLE"
    assert result.spread_q5_minus_q1 > 0.0
    assert "Q1" in result.quantile_returns
    assert "Q5" in result.quantile_returns
    assert result.coverage_mean == 1.0

    res_dict = result.as_dict()
    assert "ic_mean" in res_dict
    assert "decay_profile" in res_dict
