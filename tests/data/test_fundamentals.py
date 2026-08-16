from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from migrations.env import run_migrations
from quantlab.data.fundamentals import FundamentalValue, SqlFundamentalStore
from quantlab.domain.identity import (
    Instrument,
    InstrumentId,
    InstrumentStatus,
    InstrumentType,
)
from quantlab.infrastructure.db import DatabaseConfig, DatabaseEngine
from quantlab.infrastructure.instrument_repository import SqlInstrumentRepository


def test_fundamental_value_validation() -> None:
    inst_id = InstrumentId.from_uuid(uuid4())

    # Success
    fv = FundamentalValue(
        instrument_id=inst_id,
        period_end=date(2019, 12, 31),
        filing_date=date(2020, 2, 20),
        available_at=datetime(2020, 2, 20, 21, 0, tzinfo=UTC),
        metric="revenue",
        value=Decimal("91819000000"),
        is_restatement=False,
        source="SEC:10-K",
    )
    assert fv.metric == "revenue"

    # Float rejection
    with pytest.raises(TypeError, match="must be Decimal"):
        FundamentalValue(
            instrument_id=inst_id,
            period_end=date(2019, 12, 31),
            filing_date=date(2020, 2, 20),
            available_at=datetime(2020, 2, 20, 21, 0, tzinfo=UTC),
            metric="revenue",
            value=91819000000.0,  # type: ignore[arg-type]
            is_restatement=False,
            source="SEC:10-K",
        )


def test_sql_fundamental_store_pit_and_restatement_canary() -> None:
    engine = DatabaseEngine(DatabaseConfig(url="sqlite:///:memory:"))
    run_migrations(engine)
    inst_repo = SqlInstrumentRepository(engine)
    inst_id = InstrumentId.from_uuid(uuid4())
    inst = Instrument(
        instrument_id=inst_id,
        issuer_name="Apple Inc.",
        security_name="Apple Inc. Common Stock",
        instrument_type=InstrumentType.EQUITY,
        exchange="NASDAQ",
        currency="USD",
        active_from=date(2010, 1, 1),
        status=InstrumentStatus.ACTIVE,
    )
    inst_repo.upsert_identity(inst)
    store = SqlFundamentalStore(engine)

    # 1. Original filing for period_end 2019-12-31, available on 2020-02-20
    original_val = FundamentalValue(
        instrument_id=inst_id,
        period_end=date(2019, 12, 31),
        filing_date=date(2020, 2, 20),
        available_at=datetime(2020, 2, 20, 21, 0, tzinfo=UTC),
        metric="revenue",
        value=Decimal("91819000000"),
        is_restatement=False,
        source="SEC:10-K",
    )

    # 2. Restatement filing for period_end 2019-12-31, available on 2020-04-15
    restated_val = FundamentalValue(
        instrument_id=inst_id,
        period_end=date(2019, 12, 31),
        filing_date=date(2020, 4, 15),
        available_at=datetime(2020, 4, 15, 21, 0, tzinfo=UTC),
        metric="revenue",
        value=Decimal("91825000000"),
        is_restatement=True,
        source="SEC:10-K/A",
    )

    store.record_statements([original_val, restated_val])

    # Query before original filing was available -> None
    res_early = store.as_of(
        inst_id,
        as_of=datetime(2020, 1, 15, 0, 0, tzinfo=UTC),
        metric="revenue",
        period_end=date(2019, 12, 31),
    )
    assert res_early is None

    # Query as of 2020-03-01 -> returns original filing (91819000000)
    res_march = store.as_of(
        inst_id,
        as_of=datetime(2020, 3, 1, 0, 0, tzinfo=UTC),
        metric="revenue",
        period_end=date(2019, 12, 31),
    )
    assert res_march is not None
    assert res_march.value == Decimal("91819000000")
    assert res_march.is_restatement is False

    # Query as of 2020-05-01 -> returns restated value (91825000000)
    res_may = store.as_of(
        inst_id,
        as_of=datetime(2020, 5, 1, 0, 0, tzinfo=UTC),
        metric="revenue",
        period_end=date(2019, 12, 31),
    )
    assert res_may is not None
    assert res_may.value == Decimal("91825000000")
    assert res_may.is_restatement is True

    # Restatement history returns both in order
    history = store.restatement_history(inst_id, date(2019, 12, 31), "revenue")
    assert len(history) == 2
    assert history[0].value == Decimal("91819000000")
    assert history[1].value == Decimal("91825000000")
