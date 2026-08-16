"""Tests for multi-factor linear composite scoring."""

import uuid
from datetime import UTC, date, datetime

from quantlab.domain.identity import InstrumentId
from quantlab.factors.composites import CompositeBuilder, CompositeSpec
from quantlab.factors.contracts import FactorSnapshot, FactorValue, MissingReason


def test_composite_builder_weighting_and_normalization() -> None:
    session = date(2020, 6, 30)
    as_of = datetime(2020, 6, 30, 16, 0, tzinfo=UTC)
    universe = [InstrumentId(uuid.UUID(int=i + 1)) for i in range(5)]

    # Factor 1: momentum (weights 0.6)
    f1_vals = {
        universe[0]: FactorValue(universe[0], 1.0, None),
        universe[1]: FactorValue(universe[1], 2.0, None),
        universe[2]: FactorValue(universe[2], 3.0, None),
        universe[3]: FactorValue(universe[3], 4.0, None),
        universe[4]: FactorValue(universe[4], 5.0, None),
    }
    snap1 = FactorSnapshot(
        factor_id="momentum_12_1",
        version="v1",
        session=session,
        as_of=as_of,
        values=f1_vals,
        content_hash="h1",
    )

    # Factor 2: value (weights 0.4)
    f2_vals = {
        universe[0]: FactorValue(universe[0], 5.0, None),
        universe[1]: FactorValue(universe[1], 4.0, None),
        universe[2]: FactorValue(universe[2], 3.0, None),
        universe[3]: FactorValue(universe[3], 2.0, None),
        universe[4]: FactorValue(universe[4], 1.0, None),
    }
    snap2 = FactorSnapshot(
        factor_id="earnings_yield",
        version="v1",
        session=session,
        as_of=as_of,
        values=f2_vals,
        content_hash="h2",
    )

    spec = CompositeSpec(
        composite_id="composite-v1",
        version="v1",
        factor_weights={"momentum_12_1": 0.6, "earnings_yield": 0.4},
    )

    comp_snap = CompositeBuilder.build(
        snapshots={"momentum_12_1": snap1, "earnings_yield": snap2},
        spec=spec,
    )

    assert comp_snap.factor_id == "composite-v1"
    assert comp_snap.version == "v1"
    assert comp_snap.session == session
    assert len(comp_snap.values) == 5

    # All instruments have valid composite scores
    for u in universe:
        assert comp_snap.get_score(u) is not None


def test_composite_builder_missing_input_threshold() -> None:
    session = date(2020, 6, 30)
    as_of = datetime(2020, 6, 30, 16, 0, tzinfo=UTC)
    u1 = InstrumentId(uuid.UUID(int=1))
    u2 = InstrumentId(uuid.UUID(int=2))

    # u2 is missing in factor 1 (weight 0.6)
    f1_vals = {
        u1: FactorValue(u1, 10.0, None),
        u2: FactorValue(u2, None, MissingReason.INSUFFICIENT_HISTORY),
    }
    snap1 = FactorSnapshot("f1", "v1", session, as_of, f1_vals, "h1")

    # u2 is valid in factor 2 (weight 0.4)
    f2_vals = {
        u1: FactorValue(u1, 5.0, None),
        u2: FactorValue(u2, 5.0, None),
    }
    snap2 = FactorSnapshot("f2", "v1", session, as_of, f2_vals, "h2")

    # If min_weight_fraction = 0.5, u2 only has 0.4 weight available -> should be missing
    spec = CompositeSpec(
        composite_id="composite-v1",
        version="v1",
        factor_weights={"f1": 0.6, "f2": 0.4},
        min_weight_fraction=0.5,
    )

    comp_snap = CompositeBuilder.build(
        snapshots={"f1": snap1, "f2": snap2},
        spec=spec,
    )

    assert comp_snap.get_score(u1) is not None
    assert comp_snap.get_score(u2) is None
    assert comp_snap.values[u2].missing_reason == MissingReason.INSUFFICIENT_HISTORY
