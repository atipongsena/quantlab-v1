from __future__ import annotations

from datetime import date
from uuid import uuid4

from quantlab.domain.identity import (
    Instrument,
    InstrumentId,
    InstrumentStatus,
    InstrumentType,
)
from quantlab.universe.etf import InstrumentTypeFilter
from quantlab.universe.membership import UniverseEngine, UniverseRule


def test_etf_quarantine_and_separation() -> None:
    stock_id = InstrumentId.from_uuid(uuid4())
    stock = Instrument(
        instrument_id=stock_id,
        issuer_name="Apple Inc.",
        security_name="Apple Common Stock",
        instrument_type=InstrumentType.EQUITY,
        exchange="NASDAQ",
        currency="USD",
        active_from=date(2010, 1, 1),
        status=InstrumentStatus.ACTIVE,
    )

    etf_id = InstrumentId.from_uuid(uuid4())
    spy_etf = Instrument(
        instrument_id=etf_id,
        issuer_name="SPDR State Street",
        security_name="SPDR S&P 500 ETF Trust",
        instrument_type=InstrumentType.ETF,
        exchange="NYSE",
        currency="USD",
        active_from=date(2010, 1, 1),
        status=InstrumentStatus.ACTIVE,
    )

    all_insts = [stock, spy_etf]

    # Equity-only filter rejects ETF
    equity_filter = InstrumentTypeFilter(allowed_types={InstrumentType.EQUITY})
    assert equity_filter.allow(stock) is True
    assert equity_filter.allow(spy_etf) is False

    # ETF filter allows ETF
    etf_filter = InstrumentTypeFilter(allowed_types={InstrumentType.ETF})
    assert etf_filter.allow(stock) is False
    assert etf_filter.allow(spy_etf) is True

    # Universe engine with default rule (EQUITY only)
    engine = UniverseEngine(instruments=all_insts)
    equity_universe = engine.get_tradable_universe(
        as_of=date(2020, 1, 1),
        rules=UniverseRule(allowed_types=(InstrumentType.EQUITY,)),
    )
    assert stock_id in equity_universe
    assert etf_id not in equity_universe

    # Universe engine with ETF-only rule
    etf_universe = engine.get_tradable_universe(
        as_of=date(2020, 1, 1),
        rules=UniverseRule(allowed_types=(InstrumentType.ETF,)),
    )
    assert stock_id not in etf_universe
    assert etf_id in etf_universe
