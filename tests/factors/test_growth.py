"""Tests for growth factor family."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from quantlab.data.fundamentals import FundamentalValue
from quantlab.domain.identity import InstrumentId
from quantlab.factors.contracts import FactorContext
from quantlab.factors.growth import OperatingIncomeGrowth, RevenueGrowth


class MockGrowthPITData:
    def __init__(self, data: dict[tuple[str, date | None], FundamentalValue]) -> None:
        self._data = data

    def get_fundamental(
        self,
        instrument_id: InstrumentId,
        metric: str,
        as_of: datetime,
        period_end: date | None = None,
    ) -> FundamentalValue | None:
        if (metric, period_end) in self._data:
            return self._data[(metric, period_end)]
        return self._data.get((metric, None))


def test_growth_factors_calculation() -> None:
    session = date(2021, 3, 1)
    as_of = datetime(2021, 3, 1, 16, 0, tzinfo=UTC)
    aapl = InstrumentId(uuid.uuid4())

    # Current revenue 2020-12-31: 100B, prior revenue 2019-12-31: 80B -> growth = +25%
    rev_current = FundamentalValue(
        instrument_id=aapl,
        period_end=date(2020, 12, 31),
        filing_date=date(2021, 2, 15),
        available_at=datetime(2021, 2, 15, 21, 0, tzinfo=UTC),
        metric="revenue",
        value=Decimal(100000000000),
        is_restatement=False,
        source="synthetic",
    )
    rev_prior = FundamentalValue(
        instrument_id=aapl,
        period_end=date(2019, 12, 31),
        filing_date=date(2020, 2, 15),
        available_at=datetime(2020, 2, 15, 21, 0, tzinfo=UTC),
        metric="revenue",
        value=Decimal(80000000000),
        is_restatement=False,
        source="synthetic",
    )

    # Current op inc 2020-12-31: 30B, prior op inc 2019-12-31: 20B -> growth = +50%
    inc_current = FundamentalValue(
        instrument_id=aapl,
        period_end=date(2020, 12, 31),
        filing_date=date(2021, 2, 15),
        available_at=datetime(2021, 2, 15, 21, 0, tzinfo=UTC),
        metric="operating_income",
        value=Decimal(30000000000),
        is_restatement=False,
        source="synthetic",
    )
    inc_prior = FundamentalValue(
        instrument_id=aapl,
        period_end=date(2019, 12, 31),
        filing_date=date(2020, 2, 15),
        available_at=datetime(2020, 2, 15, 21, 0, tzinfo=UTC),
        metric="operating_income",
        value=Decimal(20000000000),
        is_restatement=False,
        source="synthetic",
    )

    mock_pit = MockGrowthPITData(
        {
            ("revenue", None): rev_current,
            ("revenue", date(2019, 12, 31)): rev_prior,
            ("operating_income", None): inc_current,
            ("operating_income", date(2019, 12, 31)): inc_prior,
        }
    )

    context = FactorContext(
        dataset_id="DATASET-v001",
        session=session,
        as_of=as_of,
        pit_data=mock_pit,  # type: ignore[arg-type]
        universe=[aapl],
    )

    rev_snap = RevenueGrowth().compute(context)
    assert abs((rev_snap.get_score(aapl) or 0.0) - 0.25) < 1e-6

    inc_snap = OperatingIncomeGrowth().compute(context)
    assert abs((inc_snap.get_score(aapl) or 0.0) - 0.50) < 1e-6
