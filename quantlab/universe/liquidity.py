from __future__ import annotations

import statistics
from collections.abc import Mapping, Sequence
from decimal import Decimal

from quantlab.domain.identity import InstrumentId
from quantlab.domain.market import MarketBar


class LiquidityFilter:
    def __init__(
        self,
        min_median_dollar_volume: Decimal,
        min_bar_count: int = 5,
    ) -> None:
        self._min_median_dollar_volume = min_median_dollar_volume
        self._min_bar_count = min_bar_count

    def calculate_median_dollar_volume(self, bars: Sequence[MarketBar]) -> Decimal | None:
        if len(bars) < self._min_bar_count:
            return None
        dollar_volumes = [bar.close * bar.volume for bar in bars]
        # Calculate median using statistics.median
        med = statistics.median(dollar_volumes)
        return Decimal(str(med))

    def filter_liquid(
        self,
        bars_by_instrument: Mapping[InstrumentId, Sequence[MarketBar]],
    ) -> set[InstrumentId]:
        liquid: set[InstrumentId] = set()
        for inst_id, bars in bars_by_instrument.items():
            med_dv = self.calculate_median_dollar_volume(bars)
            if med_dv is not None and med_dv >= self._min_median_dollar_volume:
                liquid.add(inst_id)
        return liquid
