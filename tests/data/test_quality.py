from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

from quantlab.data.quality import DataQualityAuditor
from quantlab.domain.identity import InstrumentId
from quantlab.domain.market import BarPriceSemantic, MarketBar


def test_data_quality_auditor_on_clean_and_corrupt_data() -> None:
    auditor = DataQualityAuditor()
    inst_id = InstrumentId.from_uuid(uuid4())

    # 1. Clean dataset
    clean_bars = [
        MarketBar(
            instrument_id=inst_id,
            session=date(2020, 1, 2),
            observed_at=datetime(2020, 1, 2, 21, 0, tzinfo=UTC),
            open=Decimal("100.0"),
            high=Decimal("105.0"),
            low=Decimal("99.0"),
            close=Decimal("104.0"),
            volume=Decimal("1000000"),
            semantic=BarPriceSemantic.RAW,
            source="test",
        ),
        MarketBar(
            instrument_id=inst_id,
            session=date(2020, 1, 3),
            observed_at=datetime(2020, 1, 3, 21, 0, tzinfo=UTC),
            open=Decimal("104.0"),
            high=Decimal("108.0"),
            low=Decimal("103.0"),
            close=Decimal("107.0"),
            volume=Decimal("1200000"),
            semantic=BarPriceSemantic.RAW,
            source="test",
        ),
    ]

    clean_report = auditor.audit_market_bars(
        dataset_id="clean_bars",
        bars=clean_bars,
        as_of=datetime(2020, 1, 4, 0, 0, tzinfo=UTC),
    )
    assert clean_report.overall_status == "PASS"
    assert clean_report.confidence_score == 1.0

    # 2. Future observation failure
    future_report = auditor.audit_market_bars(
        dataset_id="future_bars",
        bars=clean_bars,
        as_of=datetime(2020, 1, 1, 0, 0, tzinfo=UTC),  # as_of before observations
    )
    assert future_report.overall_status == "FAIL"
    assert any(c.name == "temporal_integrity" and c.status == "FAIL" for c in future_report.checks)
