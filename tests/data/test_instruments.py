from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest

from quantlab.data.instruments import (
    InstrumentIdentityError,
    resolve_symbol_in_memory,
    validate_non_overlapping_history,
)
from quantlab.domain.identity import (
    Instrument,
    InstrumentId,
    InstrumentStatus,
    InstrumentType,
    SymbolHistory,
)


def test_overlapping_history_rejection() -> None:
    inst1 = InstrumentId.from_uuid(uuid4())
    inst2 = InstrumentId.from_uuid(uuid4())

    h1 = SymbolHistory(
        instrument_id=inst1,
        symbol="XYZ",
        exchange="NASDAQ",
        valid_from=date(2020, 1, 1),
        valid_to=date(2021, 12, 31),
        source="test",
    )
    # Overlaps with h1
    h2 = SymbolHistory(
        instrument_id=inst2,
        symbol="XYZ",
        exchange="NASDAQ",
        valid_from=date(2021, 6, 1),
        valid_to=date(2022, 12, 31),
        source="test",
    )

    with pytest.raises(InstrumentIdentityError, match="Overlapping"):
        validate_non_overlapping_history([h1, h2])


def test_historical_symbol_resolution_and_ticker_reuse() -> None:
    old_co = InstrumentId.from_uuid(uuid4())
    new_co = InstrumentId.from_uuid(uuid4())

    h1 = SymbolHistory(
        instrument_id=old_co,
        symbol="XYZ",
        exchange="NASDAQ",
        valid_from=date(2015, 1, 1),
        valid_to=date(2019, 12, 31),
        source="test",
    )
    h2 = SymbolHistory(
        instrument_id=new_co,
        symbol="XYZ",
        exchange="NASDAQ",
        valid_from=date(2021, 1, 1),
        valid_to=None,
        source="test",
    )

    histories = [h1, h2]
    validate_non_overlapping_history(histories)

    # Resolution in 2018 resolves to old_co
    assert resolve_symbol_in_memory(histories, "XYZ", "NASDAQ", date(2018, 6, 1)) == old_co

    # Resolution in 2020 (dormant gap) resolves to None
    assert resolve_symbol_in_memory(histories, "XYZ", "NASDAQ", date(2020, 6, 1)) is None

    # Resolution in 2022 resolves to new_co
    assert resolve_symbol_in_memory(histories, "XYZ", "NASDAQ", date(2022, 6, 1)) == new_co


def test_rename_invariance() -> None:
    meta_id = InstrumentId.from_uuid(uuid4())

    h_fb = SymbolHistory(
        instrument_id=meta_id,
        symbol="FB",
        exchange="NASDAQ",
        valid_from=date(2012, 5, 18),
        valid_to=date(2022, 6, 8),
        source="test",
    )
    h_meta = SymbolHistory(
        instrument_id=meta_id,
        symbol="META",
        exchange="NASDAQ",
        valid_from=date(2022, 6, 9),
        valid_to=None,
        source="test",
    )

    histories = [h_fb, h_meta]
    validate_non_overlapping_history(histories)

    # Same instrument_id resolved under both FB and META depending on date
    assert resolve_symbol_in_memory(histories, "FB", "NASDAQ", date(2020, 1, 1)) == meta_id
    assert resolve_symbol_in_memory(histories, "META", "NASDAQ", date(2020, 1, 1)) is None

    assert resolve_symbol_in_memory(histories, "FB", "NASDAQ", date(2023, 1, 1)) is None
    assert resolve_symbol_in_memory(histories, "META", "NASDAQ", date(2023, 1, 1)) == meta_id


def test_delisted_historical_lookup() -> None:
    delist_id = InstrumentId.from_uuid(uuid4())
    inst = Instrument(
        instrument_id=delist_id,
        issuer_name="Delisted Corp",
        security_name="Delisted Corp Common Stock",
        instrument_type=InstrumentType.EQUITY,
        exchange="NYSE",
        currency="USD",
        active_from=date(2010, 1, 1),
        active_to=date(2021, 12, 31),
        status=InstrumentStatus.DELISTED,
    )
    assert inst.status == InstrumentStatus.DELISTED

    h = SymbolHistory(
        instrument_id=delist_id,
        symbol="DEAD",
        exchange="NYSE",
        valid_from=date(2010, 1, 1),
        valid_to=date(2021, 12, 31),
        source="test",
    )

    assert resolve_symbol_in_memory([h], "DEAD", "NYSE", date(2020, 1, 1)) == delist_id
    assert resolve_symbol_in_memory([h], "DEAD", "NYSE", date(2022, 1, 1)) is None
