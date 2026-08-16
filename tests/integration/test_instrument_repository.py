from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest

from migrations.env import run_migrations
from quantlab.data.instruments import InstrumentIdentityError
from quantlab.domain.identity import (
    Instrument,
    InstrumentId,
    InstrumentStatus,
    InstrumentType,
    SymbolHistory,
)
from quantlab.infrastructure.db import DatabaseConfig, DatabaseEngine
from quantlab.infrastructure.instrument_repository import SqlInstrumentRepository


def test_sql_instrument_repository_crud_and_resolution() -> None:
    engine = DatabaseEngine(DatabaseConfig(url="sqlite:///:memory:"))
    run_migrations(engine)
    repo = SqlInstrumentRepository(engine)

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

    repo.upsert_identity(aapl_inst, [aapl_history])

    # Fetch and verify
    retrieved = repo.get_instrument(aapl_id)
    assert retrieved is not None
    assert retrieved.issuer_name == "Apple Inc."

    # History
    histories = repo.history(aapl_id)
    assert len(histories) == 1
    assert histories[0].symbol == "AAPL"

    # Resolution
    resolved = repo.resolve("AAPL", "NASDAQ", date(2023, 1, 1))
    assert resolved == aapl_id

    # Resolution before listing returns None
    assert repo.resolve("AAPL", "NASDAQ", date(1979, 1, 1)) is None


def test_sql_instrument_repository_rejects_overlapping_symbols() -> None:
    engine = DatabaseEngine(DatabaseConfig(url="sqlite:///:memory:"))
    run_migrations(engine)
    repo = SqlInstrumentRepository(engine)

    id1 = InstrumentId.from_uuid(uuid4())
    id2 = InstrumentId.from_uuid(uuid4())

    inst1 = Instrument(
        instrument_id=id1,
        issuer_name="First Co",
        security_name="First Co Common",
        instrument_type=InstrumentType.EQUITY,
        exchange="NASDAQ",
        currency="USD",
        active_from=date(2020, 1, 1),
        active_to=None,
        status=InstrumentStatus.ACTIVE,
    )
    h1 = SymbolHistory(
        instrument_id=id1,
        symbol="XYZ",
        exchange="NASDAQ",
        valid_from=date(2020, 1, 1),
        valid_to=date(2021, 12, 31),
        source="test",
    )
    repo.upsert_identity(inst1, [h1])

    inst2 = Instrument(
        instrument_id=id2,
        issuer_name="Second Co",
        security_name="Second Co Common",
        instrument_type=InstrumentType.EQUITY,
        exchange="NASDAQ",
        currency="USD",
        active_from=date(2021, 1, 1),
        active_to=None,
        status=InstrumentStatus.ACTIVE,
    )
    # Overlaps with inst1 on 2021
    h2 = SymbolHistory(
        instrument_id=id2,
        symbol="XYZ",
        exchange="NASDAQ",
        valid_from=date(2021, 6, 1),
        valid_to=date(2022, 12, 31),
        source="test",
    )

    with pytest.raises(InstrumentIdentityError, match="Overlapping"):
        repo.upsert_identity(inst2, [h2])
