from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from migrations.env import run_migrations
from quantlab.data.corporate_actions import (
    SqlCorporateActionStore,
    apply_adjustments,
    compute_cumulative_adjustment_factors,
)
from quantlab.data.market_bars import MarketBarStore
from quantlab.data.normalization import NormalizationError, NormalizationPipeline
from quantlab.domain.corporate_actions import CorporateAction, CorporateActionType
from quantlab.domain.identity import (
    Instrument,
    InstrumentId,
    InstrumentStatus,
    InstrumentType,
    SymbolHistory,
)
from quantlab.domain.market import BarPriceSemantic, MarketBar
from quantlab.infrastructure.analytical_store import LocalAnalyticalStore
from quantlab.infrastructure.db import DatabaseConfig, DatabaseEngine
from quantlab.infrastructure.instrument_repository import SqlInstrumentRepository


def test_split_and_dividend_cumulative_adjustments() -> None:
    inst_id = InstrumentId.from_uuid(uuid4())

    # 3 daily bars
    b1 = MarketBar(
        instrument_id=inst_id,
        session=date(2020, 8, 27),
        observed_at=datetime(2020, 8, 27, 21, 0, tzinfo=UTC),
        open=Decimal("400.0"),
        high=Decimal("410.0"),
        low=Decimal("395.0"),
        close=Decimal("400.0"),
        volume=Decimal("1000000"),
        semantic=BarPriceSemantic.RAW,
        source="test",
    )
    b2 = MarketBar(
        instrument_id=inst_id,
        session=date(2020, 8, 28),
        observed_at=datetime(2020, 8, 28, 21, 0, tzinfo=UTC),
        open=Decimal("400.0"),
        high=Decimal("420.0"),
        low=Decimal("400.0"),
        close=Decimal("400.0"),
        volume=Decimal("1000000"),
        semantic=BarPriceSemantic.RAW,
        source="test",
    )
    b3 = MarketBar(
        instrument_id=inst_id,
        session=date(2020, 8, 31),
        observed_at=datetime(2020, 8, 31, 21, 0, tzinfo=UTC),
        open=Decimal("100.0"),
        high=Decimal("105.0"),
        low=Decimal("98.0"),
        close=Decimal("100.0"),
        volume=Decimal("4000000"),
        semantic=BarPriceSemantic.RAW,
        source="test",
    )
    bars = [b1, b2, b3]

    # 4-for-1 split effective on 2020-08-31
    split_action = CorporateAction(
        instrument_id=inst_id,
        action_type=CorporateActionType.SPLIT,
        effective_at=date(2020, 8, 31),
        announced_at=datetime(2020, 7, 30, 9, 0, tzinfo=UTC),
        available_at=datetime(2020, 7, 30, 9, 0, tzinfo=UTC),
        ratio=Decimal("4.0"),
        cash_amount=None,
        source="test",
    )

    factors = compute_cumulative_adjustment_factors(bars, [split_action])
    # b1 and b2 should have price factor 0.25 (1/4) and volume factor 4.0
    assert factors[date(2020, 8, 27)] == (Decimal("0.25"), Decimal("4.0"))
    assert factors[date(2020, 8, 28)] == (Decimal("0.25"), Decimal("4.0"))
    # b3 is on split date, factor is 1.0
    assert factors[date(2020, 8, 31)] == (Decimal("1"), Decimal("1"))

    adjusted = apply_adjustments(bars, [split_action])
    assert len(adjusted) == 3
    assert adjusted[0].close == Decimal("100.000000")
    assert adjusted[0].volume == Decimal("4000000.0000")
    assert adjusted[2].close == Decimal("100.000000")


def test_normalization_pipeline_handles_valid_data_and_rejects_missing_open(
    tmp_path: Path,
) -> None:
    engine = DatabaseEngine(DatabaseConfig(url="sqlite:///:memory:"))
    run_migrations(engine)
    inst_repo = SqlInstrumentRepository(engine)
    action_store = SqlCorporateActionStore(engine)

    analytical_store = LocalAnalyticalStore(tmp_path)
    bar_store = MarketBarStore(analytical_store)

    pipeline = NormalizationPipeline(bar_store, action_store)

    aapl_id = InstrumentId.from_uuid(uuid4())
    aapl_inst = Instrument(
        instrument_id=aapl_id,
        issuer_name="Apple Inc.",
        security_name="Apple Inc. Common Stock",
        instrument_type=InstrumentType.EQUITY,
        exchange="NASDAQ",
        currency="USD",
        active_from=date(2020, 1, 1),
        active_to=None,
        status=InstrumentStatus.ACTIVE,
    )
    aapl_history = SymbolHistory(
        instrument_id=aapl_id,
        symbol="AAPL",
        exchange="NASDAQ",
        valid_from=date(2020, 1, 1),
        valid_to=None,
        source="test",
    )
    inst_repo.upsert_identity(aapl_inst, [aapl_history])

    # Valid prices & actions CSV
    valid_prices = (
        "symbol,date,open,high,low,close,volume,observed_at,source\n"
        "AAPL,2020-01-02,100,105,95,102,1000000,2020-01-02T21:00:00Z,test\n"
        "AAPL,2020-01-03,102,106,100,105,1200000,2020-01-03T21:00:00Z,test\n"
    )
    valid_actions = (
        "symbol,action_type,effective_date,ratio,cash_amount,announced_at,available_at,source\n"
    )

    bar_cnt, act_cnt = pipeline.normalize_eod_and_actions(
        valid_prices, valid_actions, inst_repo, default_exchange="NASDAQ"
    )
    assert bar_cnt == 2
    assert act_cnt == 0

    # Canary case: Missing open price
    corrupted_prices = (
        "symbol,date,open,high,low,close,volume,observed_at,source\n"
        "AAPL,2021-06-15,,130,128,129,500000,2021-06-15T21:00:00Z,test\n"
    )
    with pytest.raises(NormalizationError, match="Missing required price field 'open'"):
        pipeline.normalize_eod_and_actions(
            corrupted_prices, valid_actions, inst_repo, default_exchange="NASDAQ"
        )

    # Weekend rejection
    weekend_prices = (
        "symbol,date,open,high,low,close,volume,observed_at,source\n"
        "AAPL,2020-01-04,100,105,95,102,1000000,2020-01-04T21:00:00Z,test\n"
    )
    with pytest.raises(NormalizationError, match="weekend"):
        pipeline.normalize_eod_and_actions(
            weekend_prices, valid_actions, inst_repo, default_exchange="NASDAQ"
        )
