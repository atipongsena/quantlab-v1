"""Tests for quality factor family."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from quantlab.data.fundamentals import FundamentalValue
from quantlab.domain.identity import InstrumentId
from quantlab.factors.contracts import FactorContext
from quantlab.factors.quality import ROA, ROE, AccrualQuality, GrossProfitability


class MockQualityPITData:
    def __init__(self, fundamentals: dict[str, FundamentalValue]) -> None:
        self._fundamentals = fundamentals

    def get_fundamental(
        self,
        instrument_id: InstrumentId,
        metric: str,
        as_of: datetime,
        period_end: date | None = None,
    ) -> FundamentalValue | None:
        return self._fundamentals.get(metric)


def test_quality_factors_calculation() -> None:
    session = date(2020, 3, 1)
    as_of = datetime(2020, 3, 1, 16, 0, tzinfo=UTC)
    aapl = InstrumentId(uuid.uuid4())

    net_income_val = FundamentalValue(
        instrument_id=aapl,
        period_end=date(2019, 12, 31),
        filing_date=date(2020, 2, 20),
        available_at=datetime(2020, 2, 20, 21, 0, tzinfo=UTC),
        metric="net_income",
        value=Decimal(20000000000),
        is_restatement=False,
        source="synthetic",
    )
    equity_val = FundamentalValue(
        instrument_id=aapl,
        period_end=date(2019, 12, 31),
        filing_date=date(2020, 2, 20),
        available_at=datetime(2020, 2, 20, 21, 0, tzinfo=UTC),
        metric="stockholders_equity",
        value=Decimal(100000000000),
        is_restatement=False,
        source="synthetic",
    )
    assets_val = FundamentalValue(
        instrument_id=aapl,
        period_end=date(2019, 12, 31),
        filing_date=date(2020, 2, 20),
        available_at=datetime(2020, 2, 20, 21, 0, tzinfo=UTC),
        metric="total_assets",
        value=Decimal(200000000000),
        is_restatement=False,
        source="synthetic",
    )
    gross_profit_val = FundamentalValue(
        instrument_id=aapl,
        period_end=date(2019, 12, 31),
        filing_date=date(2020, 2, 20),
        available_at=datetime(2020, 2, 20, 21, 0, tzinfo=UTC),
        metric="gross_profit",
        value=Decimal(40000000000),
        is_restatement=False,
        source="synthetic",
    )

    mock_pit = MockQualityPITData(
        {
            "net_income": net_income_val,
            "stockholders_equity": equity_val,
            "total_assets": assets_val,
            "gross_profit": gross_profit_val,
        }
    )

    context = FactorContext(
        dataset_id="DATASET-v001",
        session=session,
        as_of=as_of,
        pit_data=mock_pit,  # type: ignore[arg-type]
        universe=[aapl],
    )

    # ROE: 20B / 100B = 0.20
    roe_snap = ROE().compute(context)
    assert abs((roe_snap.get_score(aapl) or 0.0) - 0.20) < 1e-6

    # ROA: 20B / 200B = 0.10
    roa_snap = ROA().compute(context)
    assert abs((roa_snap.get_score(aapl) or 0.0) - 0.10) < 1e-6

    # Gross Profitability: 40B / 200B = 0.20
    gp_snap = GrossProfitability().compute(context)
    assert abs((gp_snap.get_score(aapl) or 0.0) - 0.20) < 1e-6

    # Accrual Quality
    aq_snap = AccrualQuality().compute(context)
    assert aq_snap.get_score(aapl) is not None
