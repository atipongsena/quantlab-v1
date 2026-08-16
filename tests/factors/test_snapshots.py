"""Tests for FactorSnapshot construction and order invariance."""

import uuid
from datetime import UTC, date, datetime

from quantlab.domain.identity import InstrumentId
from quantlab.factors.contracts import FactorSnapshot, FactorValue, MissingReason
from quantlab.factors.snapshots import build_factor_snapshot, compute_composite_availability


def test_factor_snapshot_order_invariant_hashing() -> None:
    session = date(2020, 3, 1)
    as_of = datetime(2020, 3, 1, 16, 0, tzinfo=UTC)
    aapl = InstrumentId(uuid.uuid4())
    msft = InstrumentId(uuid.uuid4())
    goog = InstrumentId(uuid.uuid4())

    dict_order_1 = {
        aapl: FactorValue(instrument_id=aapl, value=0.12),
        msft: FactorValue(instrument_id=msft, value=0.08),
        goog: FactorValue(
            instrument_id=goog, value=None, missing_reason=MissingReason.INSUFFICIENT_HISTORY
        ),
    }

    dict_order_2 = {
        goog: FactorValue(
            instrument_id=goog, value=None, missing_reason=MissingReason.INSUFFICIENT_HISTORY
        ),
        msft: FactorValue(instrument_id=msft, value=0.08),
        aapl: FactorValue(instrument_id=aapl, value=0.12),
    }

    snap_1 = FactorSnapshot.create("momentum", "v1", session, as_of, dict_order_1)
    snap_2 = FactorSnapshot.create("momentum", "v1", session, as_of, dict_order_2)

    assert snap_1.content_hash == snap_2.content_hash
    assert snap_1.valid_scores() == {aapl: 0.12, msft: 0.08}
    assert snap_1.get_score(aapl) == 0.12
    assert snap_1.get_score(goog) is None


def test_build_factor_snapshot_universe_alignment() -> None:
    session = date(2020, 3, 1)
    as_of = datetime(2020, 3, 1, 16, 0, tzinfo=UTC)
    aapl = InstrumentId(uuid.uuid4())
    msft = InstrumentId(uuid.uuid4())
    tsla = InstrumentId(uuid.uuid4())

    raw_values = {aapl: 0.15, msft: None}
    snapshot = build_factor_snapshot(
        factor_id="mom_test",
        version="v1",
        session=session,
        as_of=as_of,
        raw_values=raw_values,
        universe=[aapl, msft, tsla],
    )

    assert snapshot.get_score(aapl) == 0.15
    assert snapshot.values[msft].missing_reason == MissingReason.INSUFFICIENT_HISTORY
    assert snapshot.values[tsla].missing_reason == MissingReason.NOT_IN_UNIVERSE


def test_composite_availability_is_max_input_availability() -> None:
    session = date(2020, 3, 1)
    t1 = datetime(2020, 3, 1, 16, 0, tzinfo=UTC)
    t2 = datetime(2020, 3, 1, 20, 0, tzinfo=UTC)
    aapl = InstrumentId(uuid.uuid4())

    s1 = FactorSnapshot.create(
        "f1", "v1", session, t1, {aapl: FactorValue(instrument_id=aapl, value=1.0)}
    )
    s2 = FactorSnapshot.create(
        "f2", "v1", session, t2, {aapl: FactorValue(instrument_id=aapl, value=2.0)}
    )

    composite_as_of = compute_composite_availability([s1, s2])
    assert composite_as_of == t2
