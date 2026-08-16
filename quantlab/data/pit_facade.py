from __future__ import annotations

from datetime import date, datetime

from quantlab.data.corporate_actions import CorporateActionStore, apply_adjustments
from quantlab.data.fundamentals import FundamentalStore, FundamentalValue
from quantlab.data.macro import MacroStore, MacroVintage
from quantlab.data.market_bars import MarketBarStore
from quantlab.domain.identity import InstrumentId
from quantlab.domain.market import BarPriceSemantic, MarketBar
from quantlab.infrastructure.instrument_repository import InstrumentRepository
from quantlab.universe.membership import UniverseEngine, UniverseRule


class PointInTimeDataFacade:
    def __init__(
        self,
        instrument_repo: InstrumentRepository,
        bar_store: MarketBarStore,
        action_store: CorporateActionStore,
        fund_store: FundamentalStore,
        macro_store: MacroStore,
        universe_engine: UniverseEngine,
    ) -> None:
        self._instrument_repo = instrument_repo
        self._bar_store = bar_store
        self._action_store = action_store
        self._fund_store = fund_store
        self._macro_store = macro_store
        self._universe_engine = universe_engine

    def get_market_bars(
        self,
        instrument_id: InstrumentId,
        start_date: date,
        end_date: date,
        as_of: datetime,
        adjusted: bool = True,
    ) -> tuple[MarketBar, ...]:
        raw_bars = self._bar_store.get_bars(
            instrument_id=instrument_id,
            start_date=start_date,
            end_date=end_date,
            semantic=BarPriceSemantic.RAW,
        )
        # Filter by observed_at <= as_of
        valid_raw = [b for b in raw_bars if b.observed_at <= as_of]
        if not adjusted or not valid_raw:
            return tuple(valid_raw)

        actions = self._action_store.get_actions(
            instrument_id=instrument_id,
            start_date=start_date,
            end_date=as_of.date(),
        )
        adj_bars = apply_adjustments(valid_raw, actions, as_of=as_of)
        return tuple(adj_bars)

    def get_fundamentals(
        self,
        instrument_id: InstrumentId,
        as_of: datetime,
        metric: str,
        period_end: date | None = None,
    ) -> FundamentalValue | None:
        return self._fund_store.as_of(
            instrument_id=instrument_id,
            as_of=as_of,
            metric=metric,
            period_end=period_end,
        )

    def get_fundamental(
        self,
        instrument_id: InstrumentId,
        metric: str,
        as_of: datetime,
        period_end: date | None = None,
    ) -> FundamentalValue | None:
        return self.get_fundamentals(
            instrument_id=instrument_id,
            as_of=as_of,
            metric=metric,
            period_end=period_end,
        )

    def get_macro(
        self,
        series_id: str,
        as_of: datetime,
        period_date: date | None = None,
    ) -> MacroVintage | None:
        return self._macro_store.as_of(
            series_id=series_id,
            as_of=as_of,
            period_date=period_date,
        )

    def get_tradable_universe(
        self,
        as_of: date,
        rules: UniverseRule | None = None,
    ) -> tuple[InstrumentId, ...]:
        return self._universe_engine.get_tradable_universe(as_of=as_of, rules=rules)


PointInTimeData = PointInTimeDataFacade
