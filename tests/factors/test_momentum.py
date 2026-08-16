"""Tests for momentum factor family."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from quantlab.domain.identity import InstrumentId
from quantlab.domain.market import BarPriceSemantic, MarketBar
from quantlab.factors.contracts import FactorContext, MissingReason
from quantlab.factors.momentum import Momentum6M1M, Momentum12M1M


class MockMomentumPITData:
    def __init__(self, bars: tuple[MarketBar, ...]) -> None:
        self._bars = bars

    def get_market_bars(
        self,
        instrument_id: InstrumentId,
        start_date: date,
        end_date: date,
        as_of: datetime,
        adjusted: bool = True,
    ) -> tuple[MarketBar, ...]:
        return self._bars


def test_momentum_12_1_calculation() -> None:
    session = date(2020, 12, 31)
    as_of = datetime(2020, 12, 31, 16, 0, tzinfo=UTC)
    aapl = InstrumentId(uuid.uuid4())

    # Build 300 bars with increasing close prices: 100.0, 101.0, ..., 399.0
    bars = []
    for i in range(300):
        d = date(2019, 1, 1) + (session - date(2019, 1, 1)) * i // 300
        p = Decimal(100 + i)
        bars.append(
            MarketBar(
                instrument_id=aapl,
                session=d,
                observed_at=as_of,
                open=p,
                high=p,
                low=p,
                close=p,
                volume=Decimal(1000),
                semantic=BarPriceSemantic.ADJUSTED,
                source="synthetic",
            )
        )

    mock_pit = MockMomentumPITData(tuple(bars))
    context = FactorContext(
        dataset_id="DATASET-v001",
        session=session,
        as_of=as_of,
        pit_data=mock_pit,  # type: ignore[arg-type]
        universe=[aapl],
    )

    factor = Momentum12M1M()
    snapshot = factor.compute(context)

    # Valid score computed
    score = snapshot.get_score(aapl)
    assert score is not None
    assert score > 0.0

    # 6M momentum
    factor_6m = Momentum6M1M()
    snap_6m = factor_6m.compute(context)
    score_6m = snap_6m.get_score(aapl)
    assert score_6m is not None
    assert score_6m > 0.0


def test_momentum_insufficient_history() -> None:
    session = date(2020, 12, 31)
    as_of = datetime(2020, 12, 31, 16, 0, tzinfo=UTC)
    aapl = InstrumentId(uuid.uuid4())

    # Only 50 bars
    bars = [
        MarketBar(
            instrument_id=aapl,
            session=date(2020, 1, 1),
            observed_at=as_of,
            open=Decimal(100),
            high=Decimal(100),
            low=Decimal(100),
            close=Decimal(100),
            volume=Decimal(1000),
            semantic=BarPriceSemantic.ADJUSTED,
            source="synthetic",
        )
        for _ in range(50)
    ]

    mock_pit = MockMomentumPITData(tuple(bars))
    context = FactorContext(
        dataset_id="DATASET-v001",
        session=session,
        as_of=as_of,
        pit_data=mock_pit,  # type: ignore[arg-type]
        universe=[aapl],
    )

    factor = Momentum12M1M()
    snapshot = factor.compute(context)
    assert snapshot.get_score(aapl) is None
    assert snapshot.values[aapl].missing_reason == MissingReason.INSUFFICIENT_HISTORY
