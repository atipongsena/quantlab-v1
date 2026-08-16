from __future__ import annotations

from datetime import date
from uuid import uuid4

from quantlab.domain.identity import (
    Instrument,
    InstrumentId,
    InstrumentStatus,
    InstrumentType,
)
from quantlab.universe.membership import UniverseEngine


def test_survivorship_bias_free_historical_universe() -> None:
    # 1. Company listed entire time
    aapl_id = InstrumentId.from_uuid(uuid4())
    aapl = Instrument(
        instrument_id=aapl_id,
        issuer_name="Apple Inc.",
        security_name="Apple Common Stock",
        instrument_type=InstrumentType.EQUITY,
        exchange="NASDAQ",
        currency="USD",
        active_from=date(1980, 12, 12),
        active_to=None,
        status=InstrumentStatus.ACTIVE,
    )

    # 2. Company IPO in 2021
    ipo_id = InstrumentId.from_uuid(uuid4())
    ipo_co = Instrument(
        instrument_id=ipo_id,
        issuer_name="IPO 2021 Corp",
        security_name="IPO 2021 Common",
        instrument_type=InstrumentType.EQUITY,
        exchange="NASDAQ",
        currency="USD",
        active_from=date(2021, 6, 1),
        active_to=None,
        status=InstrumentStatus.ACTIVE,
    )

    # 3. Company delisted at end of 2020
    delist_id = InstrumentId.from_uuid(uuid4())
    delist_co = Instrument(
        instrument_id=delist_id,
        issuer_name="Old Co",
        security_name="Old Co Common",
        instrument_type=InstrumentType.EQUITY,
        exchange="NASDAQ",
        currency="USD",
        active_from=date(2010, 1, 1),
        active_to=date(2020, 12, 31),
        status=InstrumentStatus.DELISTED,
    )

    all_instruments = [aapl, ipo_co, delist_co]
    engine = UniverseEngine(instruments=all_instruments)

    # As of 2020-06-01: AAPL and Old Co should be in universe; IPO Co should NOT be in universe
    u_2020 = engine.get_tradable_universe(as_of=date(2020, 6, 1))
    assert aapl_id in u_2020
    assert delist_id in u_2020
    assert ipo_id not in u_2020

    # As of 2021-07-01: AAPL and IPO Co should be in universe; Old Co (delisted) should NOT be
    u_2021 = engine.get_tradable_universe(as_of=date(2021, 7, 1))
    assert aapl_id in u_2021
    assert ipo_id in u_2021
    assert delist_id not in u_2021
