from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from migrations.env import run_migrations
from quantlab.data.corporate_actions import SqlCorporateActionStore
from quantlab.data.fundamentals import FundamentalValue, SqlFundamentalStore
from quantlab.data.macro import MacroVintage, SqlMacroStore
from quantlab.data.market_bars import MarketBarStore
from quantlab.data.pit_facade import PointInTimeDataFacade
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
from quantlab.universe.membership import UniverseEngine


def test_point_in_time_data_facade_cross_sectional_alignment(tmp_path: Path) -> None:
    engine = DatabaseEngine(DatabaseConfig(url="sqlite:///:memory:"))
    run_migrations(engine)

    inst_repo = SqlInstrumentRepository(engine)
    action_store = SqlCorporateActionStore(engine)
    fund_store = SqlFundamentalStore(engine)
    macro_store = SqlMacroStore(engine)

    analytical_store = LocalAnalyticalStore(tmp_path)
    bar_store = MarketBarStore(analytical_store)

    inst_id = InstrumentId.from_uuid(uuid4())
    inst = Instrument(
        instrument_id=inst_id,
        issuer_name="Apple Inc.",
        security_name="Apple Common Stock",
        instrument_type=InstrumentType.EQUITY,
        exchange="NASDAQ",
        currency="USD",
        active_from=date(2010, 1, 1),
        status=InstrumentStatus.ACTIVE,
    )
    history = SymbolHistory(
        instrument_id=inst_id,
        symbol="AAPL",
        exchange="NASDAQ",
        valid_from=date(2010, 1, 1),
        valid_to=None,
        source="test",
    )
    inst_repo.upsert_identity(inst, [history])

    universe_engine = UniverseEngine(instruments=[inst], bar_store=bar_store)

    facade = PointInTimeDataFacade(
        instrument_repo=inst_repo,
        bar_store=bar_store,
        action_store=action_store,
        fund_store=fund_store,
        macro_store=macro_store,
        universe_engine=universe_engine,
    )

    # 1. Market bar
    bar = MarketBar(
        instrument_id=inst_id,
        session=date(2020, 1, 2),
        observed_at=datetime(2020, 1, 2, 21, 0, tzinfo=UTC),
        open=Decimal("300.0"),
        high=Decimal("305.0"),
        low=Decimal("298.0"),
        close=Decimal("300.0"),
        volume=Decimal("1000000"),
        semantic=BarPriceSemantic.RAW,
        source="test",
    )
    bar_store.write_daily_bars([bar])

    # 2. Corporate action 4-for-1 split on 2020-08-31
    split_act = CorporateAction(
        instrument_id=inst_id,
        action_type=CorporateActionType.SPLIT,
        effective_at=date(2020, 8, 31),
        announced_at=datetime(2020, 7, 30, 9, 0, tzinfo=UTC),
        available_at=datetime(2020, 7, 30, 9, 0, tzinfo=UTC),
        ratio=Decimal("4.0"),
        cash_amount=None,
        source="test",
    )
    action_store.record_action(split_act)

    # 3. Fundamental filing on 2020-02-20
    fund = FundamentalValue(
        instrument_id=inst_id,
        period_end=date(2019, 12, 31),
        filing_date=date(2020, 2, 20),
        available_at=datetime(2020, 2, 20, 21, 0, tzinfo=UTC),
        metric="eps",
        value=Decimal("1.25"),
        is_restatement=False,
        source="SEC",
    )
    fund_store.record_statement(fund)

    # 4. Macro release on 2020-01-30
    macro = MacroVintage(
        series_id="GDP",
        period_date=date(2019, 10, 1),
        release_time=datetime(2020, 1, 30, 13, 30, tzinfo=UTC),
        value=Decimal("21700.0"),
        source="BEA",
    )
    macro_store.record_vintage(macro)

    # Query as of 2020-01-15:
    # Bar is available, unadjusted close is 300.0 (since split was not known/available yet)
    bars_jan = facade.get_market_bars(
        inst_id,
        date(2020, 1, 1),
        date(2020, 1, 5),
        as_of=datetime(2020, 1, 15, 0, 0, tzinfo=UTC),
    )
    assert len(bars_jan) == 1
    assert bars_jan[0].close == Decimal("300.000000")

    # Fundamentals as of 2020-01-15 -> None (filing available on 2020-02-20)
    assert (
        facade.get_fundamentals(
            inst_id, as_of=datetime(2020, 1, 15, 0, 0, tzinfo=UTC), metric="eps"
        )
        is None
    )

    # Query as of 2020-08-31:
    # Bar is adjusted for split -> 75.0 (300 / 4)
    bars_aug = facade.get_market_bars(
        inst_id,
        date(2020, 1, 1),
        date(2020, 1, 5),
        as_of=datetime(2020, 8, 31, 23, 59, tzinfo=UTC),
    )
    assert len(bars_aug) == 1
    assert bars_aug[0].close == Decimal("75.000000")

    # Fundamentals as of 2020-08-31 -> 1.25
    fund_aug = facade.get_fundamentals(
        inst_id, as_of=datetime(2020, 8, 31, 0, 0, tzinfo=UTC), metric="eps"
    )
    assert fund_aug is not None
    assert fund_aug.value == Decimal("1.25")

    # Macro as of 2020-08-31 -> 21700.0
    macro_aug = facade.get_macro(
        "GDP",
        as_of=datetime(2020, 8, 31, 0, 0, tzinfo=UTC),
        period_date=date(2019, 10, 1),
    )
    assert macro_aug is not None
    assert macro_aug.value == Decimal("21700.0")

    # Universe as of 2020-08-31
    univ = facade.get_tradable_universe(as_of=date(2020, 8, 31))
    assert inst_id in univ
