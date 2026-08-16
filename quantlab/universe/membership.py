from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from quantlab.data.market_bars import MarketBarStore
from quantlab.domain.identity import Instrument, InstrumentId, InstrumentType
from quantlab.domain.market import BarPriceSemantic, MarketBar
from quantlab.infrastructure.instrument_repository import InstrumentRepository
from quantlab.universe.etf import InstrumentTypeFilter
from quantlab.universe.liquidity import LiquidityFilter


@dataclass(frozen=True, slots=True)
class UniverseRule:
    allowed_types: tuple[InstrumentType, ...] = (InstrumentType.EQUITY,)
    min_median_dollar_volume: Decimal | None = None
    liquidity_lookback_days: int = 20
    exchanges: tuple[str, ...] = ("NASDAQ", "NYSE")


class UniverseEngine:
    def __init__(
        self,
        instrument_repo: InstrumentRepository | None = None,
        bar_store: MarketBarStore | None = None,
        instruments: Sequence[Instrument] | None = None,
    ) -> None:
        self._instrument_repo = instrument_repo
        self._bar_store = bar_store
        self._instruments = list(instruments) if instruments is not None else None

    def _get_active_instruments(self, as_of: date) -> list[Instrument]:
        candidates: list[Instrument] = []
        if self._instruments is not None:
            for inst in self._instruments:
                if inst.active_from <= as_of and (
                    inst.active_to is None or as_of <= inst.active_to
                ):
                    candidates.append(inst)
        elif self._instrument_repo is not None:
            # Fetch from repository if available
            # Note: in SQL repo, we query active instruments
            # In general, if repository has list method or fallback
            pass
        return candidates

    def get_tradable_universe(
        self,
        as_of: date,
        rules: UniverseRule | None = None,
        candidate_instruments: Sequence[Instrument] | None = None,
    ) -> tuple[InstrumentId, ...]:
        active_rules = rules or UniverseRule()
        type_filter = InstrumentTypeFilter(active_rules.allowed_types)
        exchanges_upper = {e.upper() for e in active_rules.exchanges}

        # Determine candidates
        candidates: list[Instrument] = []
        source_insts = (
            list(candidate_instruments)
            if candidate_instruments is not None
            else (self._instruments if self._instruments is not None else [])
        )

        for inst in source_insts:
            # 1. Point-in-time listing active check
            is_active = inst.active_from <= as_of and (
                inst.active_to is None or as_of <= inst.active_to
            )
            if not is_active:
                continue

            # 2. Asset class / ETF filter
            if not type_filter.allow(inst):
                continue

            # 3. Exchange filter
            if exchanges_upper and inst.exchange.upper() not in exchanges_upper:
                continue

            candidates.append(inst)

        # 4. Optional Liquidity filter
        if active_rules.min_median_dollar_volume is not None and self._bar_store is not None:
            start_lookback = as_of - timedelta(days=active_rules.liquidity_lookback_days * 2)
            bars_by_inst: dict[InstrumentId, tuple[MarketBar, ...]] = {}
            for inst in candidates:
                bars = self._bar_store.get_bars(
                    instrument_id=inst.instrument_id,
                    start_date=start_lookback,
                    end_date=as_of,
                    semantic=BarPriceSemantic.RAW,
                )
                bars_by_inst[inst.instrument_id] = bars

            liq_filter = LiquidityFilter(
                min_median_dollar_volume=active_rules.min_median_dollar_volume,
                min_bar_count=min(5, active_rules.liquidity_lookback_days),
            )
            liquid_ids = liq_filter.filter_liquid(bars_by_inst)
            candidates = [c for c in candidates if c.instrument_id in liquid_ids]

        # Return sorted deterministically by InstrumentId UUID string
        sorted_ids = sorted(
            [c.instrument_id for c in candidates],
            key=lambda x: str(x.value),
        )
        return tuple(sorted_ids)
