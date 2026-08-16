from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

from migrations.env import run_migrations
from quantlab.data.fundamentals import FundamentalValue, SqlFundamentalStore
from quantlab.domain.identity import (
    Instrument,
    InstrumentId,
    InstrumentStatus,
    InstrumentType,
    SymbolHistory,
)
from quantlab.infrastructure.db import DatabaseConfig, DatabaseEngine
from quantlab.infrastructure.instrument_repository import SqlInstrumentRepository


def test_fundamentals_pit_integration_with_instruments() -> None:
    engine = DatabaseEngine(DatabaseConfig(url="sqlite:///:memory:"))
    applied = run_migrations(engine)
    assert "0003_fundamentals" in applied

    inst_repo = SqlInstrumentRepository(engine)
    fund_store = SqlFundamentalStore(engine)

    aapl_id = InstrumentId.from_uuid(uuid4())
    aapl_inst = Instrument(
        instrument_id=aapl_id,
        issuer_name="Apple Inc.",
        security_name="Apple Inc. Common Stock",
        instrument_type=InstrumentType.EQUITY,
        exchange="NASDAQ",
        currency="USD",
        active_from=date(1980, 12, 12),
        active_to=None,
        status=InstrumentStatus.ACTIVE,
    )
    aapl_history = SymbolHistory(
        instrument_id=aapl_id,
        symbol="AAPL",
        exchange="NASDAQ",
        valid_from=date(1980, 12, 12),
        valid_to=None,
        source="test",
    )
    inst_repo.upsert_identity(aapl_inst, [aapl_history])

    # Record Q1 and Q2 fundamentals
    q1 = FundamentalValue(
        instrument_id=aapl_id,
        period_end=date(2020, 3, 31),
        filing_date=date(2020, 4, 30),
        available_at=datetime(2020, 4, 30, 21, 0, tzinfo=UTC),
        metric="eps",
        value=Decimal("0.64"),
        is_restatement=False,
        source="SEC:10-Q",
    )
    q2 = FundamentalValue(
        instrument_id=aapl_id,
        period_end=date(2020, 6, 30),
        filing_date=date(2020, 7, 30),
        available_at=datetime(2020, 7, 30, 21, 0, tzinfo=UTC),
        metric="eps",
        value=Decimal("0.65"),
        is_restatement=False,
        source="SEC:10-Q",
    )
    fund_store.record_statements([q1, q2])

    # As of 2020-05-15, latest available is Q1
    pit_may = fund_store.as_of(
        aapl_id,
        as_of=datetime(2020, 5, 15, 0, 0, tzinfo=UTC),
        metric="eps",
    )
    assert pit_may is not None
    assert pit_may.period_end == date(2020, 3, 31)
    assert pit_may.value == Decimal("0.64")

    # As of 2020-08-15, latest available is Q2
    pit_aug = fund_store.as_of(
        aapl_id,
        as_of=datetime(2020, 8, 15, 0, 0, tzinfo=UTC),
        metric="eps",
    )
    assert pit_aug is not None
    assert pit_aug.period_end == date(2020, 6, 30)
    assert pit_aug.value == Decimal("0.65")
