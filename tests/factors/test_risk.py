"""Tests for risk and volatility factor family."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from quantlab.domain.identity import InstrumentId
from quantlab.domain.market import BarPriceSemantic, MarketBar
from quantlab.factors.contracts import FactorContext
from quantlab.factors.risk import Beta, MaxDrawdown252D, Volatility60D


class MockRiskPITData:
    def __init__(self, bars_map: dict[InstrumentId, tuple[MarketBar, ...]]) -> None:
        self._bars_map = bars_map

    def get_market_bars(
        self,
        instrument_id: InstrumentId,
        start_date: date,
        end_date: date,
        as_of: datetime,
        adjusted: bool = True,
    ) -> tuple[MarketBar, ...]:
        return self._bars_map.get(instrument_id, ())


def test_risk_factors_calculation() -> None:
    session = date(2020, 12, 31)
    as_of = datetime(2020, 12, 31, 16, 0, tzinfo=UTC)
    aapl = InstrumentId(uuid.uuid4())
    msft = InstrumentId(uuid.uuid4())

    # Generate 300 bars with known price trends
    aapl_bars = []
    msft_bars = []
    for i in range(300):
        d = date(2019, 1, 1) + (session - date(2019, 1, 1)) * i // 300
        p_aapl = Decimal(100 + (i % 10))  # oscillatory
        p_msft = Decimal(200 + i)  # upward trend
        aapl_bars.append(
            MarketBar(
                instrument_id=aapl,
                session=d,
                observed_at=as_of,
                open=p_aapl,
                high=p_aapl,
                low=p_aapl,
                close=p_aapl,
                volume=Decimal(1000),
                semantic=BarPriceSemantic.ADJUSTED,
                source="synthetic",
            )
        )
        msft_bars.append(
            MarketBar(
                instrument_id=msft,
                session=d,
                observed_at=as_of,
                open=p_msft,
                high=p_msft,
                low=p_msft,
                close=p_msft,
                volume=Decimal(1000),
                semantic=BarPriceSemantic.ADJUSTED,
                source="synthetic",
            )
        )

    mock_pit = MockRiskPITData({aapl: tuple(aapl_bars), msft: tuple(msft_bars)})
    context = FactorContext(
        dataset_id="DATASET-v001",
        session=session,
        as_of=as_of,
        pit_data=mock_pit,  # type: ignore[arg-type]
        universe=[aapl, msft],
    )

    # Volatility
    vol_snap = Volatility60D().compute(context)
    assert vol_snap.get_score(aapl) is not None
    assert vol_snap.get_score(msft) is not None
    assert (vol_snap.get_score(aapl) or 0.0) > 0.0

    # Max Drawdown
    dd_snap = MaxDrawdown252D().compute(context)
    assert dd_snap.get_score(aapl) is not None
    assert dd_snap.get_score(msft) is not None

    # Beta
    beta_snap = Beta().compute(context)
    assert beta_snap.get_score(aapl) is not None
    assert beta_snap.get_score(msft) is not None
