"""Execution model interfaces and next-open reference pricing."""

from __future__ import annotations

from decimal import Decimal

from quantlab.domain.market import MarketBar
from quantlab.domain.orders import Order


class NextOpenExecution:
    """Extracts next-session open price as reference price for market orders."""

    @classmethod
    def reference_price(cls, order: Order, bar: MarketBar) -> Decimal | None:
        if bar.open <= Decimal("0.0"):
            return None
        return bar.open.quantize(Decimal("0.0001"))
