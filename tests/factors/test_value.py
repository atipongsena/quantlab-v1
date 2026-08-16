"""Tests for value factor family."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from quantlab.data.fundamentals import FundamentalValue
from quantlab.domain.identity import InstrumentId
from quantlab.domain.market import BarPriceSemantic, MarketBar
from quantlab.factors.contracts import FactorContext, MissingReason
from quantlab.factors.value import BookToMarket, EarningsYield, FCFYield


class MockValuePITData:
    def __init__(
        self,
        fundamentals: dict[str, FundamentalValue],
        bars: tuple[MarketBar, ...],
    ) -> None:
        self._fundamentals = fundamentals
        self._bars = bars

    def get_fundamental(
        self,
        instrument_id: InstrumentId,
        metric: str,
        as_of: datetime,
        period_end: date | None = None,
    ) -> FundamentalValue | None:
        return self._fundamentals.get(metric)

    def get_market_bars(
        self,
        instrument_id: InstrumentId,
        start_date: date,
        end_date: date,
        as_of: datetime,
        adjusted: bool = True,
    ) -> tuple[MarketBar, ...]:
        return self._bars


def test_earnings_yield_and_book_to_market() -> None:
    session = date(2020, 3, 1)
    as_of = datetime(2020, 3, 1, 16, 0, tzinfo=UTC)
    aapl = InstrumentId(uuid.uuid4())

    net_income_val = FundamentalValue(
        instrument_id=aapl,
        period_end=date(2019, 12, 31),
        filing_date=date(2020, 2, 20),
        available_at=datetime(2020, 2, 20, 21, 0, tzinfo=UTC),
        metric="net_income",
        value=Decimal(22000000000),
        is_restatement=False,
        source="synthetic",
    )
    equity_val = FundamentalValue(
        instrument_id=aapl,
        period_end=date(2019, 12, 31),
        filing_date=date(2020, 2, 20),
        available_at=datetime(2020, 2, 20, 21, 0, tzinfo=UTC),
        metric="stockholders_equity",
        value=Decimal(90000000000),
        is_restatement=False,
        source="synthetic",
    )

    bar = MarketBar(
        instrument_id=aapl,
        session=session,
        observed_at=as_of,
        open=Decimal(200),
        high=Decimal(205),
        low=Decimal(195),
        close=Decimal(200),
        volume=Decimal(10000),
        semantic=BarPriceSemantic.ADJUSTED,
        source="synthetic",
    )

    mock_pit = MockValuePITData(
        fundamentals={"net_income": net_income_val, "stockholders_equity": equity_val},
        bars=(bar,),
    )

    context = FactorContext(
        dataset_id="DATASET-v001",
        session=session,
        as_of=as_of,
        pit_data=mock_pit,  # type: ignore[arg-type]
        universe=[aapl],
    )

    ey_factor = EarningsYield()
    ey_snap = ey_factor.compute(context)
    assert ey_snap.get_score(aapl) == 22000000000.0 / 200.0

    bm_factor = BookToMarket()
    bm_snap = bm_factor.compute(context)
    assert bm_snap.get_score(aapl) == 90000000000.0 / 200.0

    fcf_factor = FCFYield()
    fcf_snap = fcf_factor.compute(context)
    assert fcf_snap.get_score(aapl) is not None


def test_value_missing_fundamental() -> None:
    session = date(2020, 3, 1)
    as_of = datetime(2020, 3, 1, 16, 0, tzinfo=UTC)
    aapl = InstrumentId(uuid.uuid4())

    mock_pit = MockValuePITData(fundamentals={}, bars=())
    context = FactorContext(
        dataset_id="DATASET-v001",
        session=session,
        as_of=as_of,
        pit_data=mock_pit,  # type: ignore[arg-type]
        universe=[aapl],
    )

    ey_factor = EarningsYield()
    ey_snap = ey_factor.compute(context)
    assert ey_snap.get_score(aapl) is None
    assert ey_snap.values[aapl].missing_reason == MissingReason.MISSING_FUNDAMENTAL
