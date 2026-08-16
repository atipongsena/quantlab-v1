"""Golden fixture regression tests for factor evaluation determinism."""

import uuid
from datetime import UTC, date, datetime

from quantlab.domain.identity import InstrumentId
from quantlab.factors.contracts import FactorSnapshot, FactorValue
from quantlab.factors.evaluation import EvaluationSpec, FactorEvaluator, ForwardReturnView


def test_factor_evaluation_golden_determinism() -> None:
    # 5 instruments, 3 sessions, deterministic inputs
    universe = [InstrumentId(uuid.UUID(int=i + 100)) for i in range(5)]
    sessions = [date(2020, 1, 31), date(2020, 2, 28), date(2020, 3, 31)]
    as_of = datetime(2020, 4, 1, 0, 0, tzinfo=UTC)

    snapshots = []
    returns_map = {}

    for s_idx, session in enumerate(sessions):
        snap_vals = {}
        fwd_vals_1m = {}
        for i, u in enumerate(universe):
            score = float((i + 1) * (s_idx + 1))
            snap_vals[u] = FactorValue(u, score, None)
            fwd_vals_1m[u] = 0.01 * (i + 1) * (s_idx + 1)

        snapshots.append(
            FactorSnapshot(
                factor_id="golden_momentum",
                version="v1",
                session=session,
                as_of=as_of,
                values=snap_vals,
                content_hash=f"golden_{s_idx}",
            )
        )
        returns_map[(session, 21)] = fwd_vals_1m

    fwd_view = ForwardReturnView(returns=returns_map)
    evaluator = FactorEvaluator(EvaluationSpec(primary_horizon=21, num_quantiles=5))

    res1 = evaluator.evaluate(snapshots, fwd_view)
    res2 = evaluator.evaluate(snapshots, fwd_view)

    # Identical runs must produce identical content hashes and dicts
    assert res1.content_hash == res2.content_hash
    assert res1.as_dict() == res2.as_dict()
    assert res1.ic_mean == 1.0
    assert res1.rank_ic_mean == 1.0
