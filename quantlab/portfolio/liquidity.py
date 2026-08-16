"""Liquidity and ADV metrics calculation."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from quantlab.domain.identity import InstrumentId
from quantlab.domain.market import MarketBar


def compute_adv(
    bars: Sequence[MarketBar],
    instrument_id: InstrumentId,
    window: int = 20,
) -> Decimal:
    """Compute average daily volume in shares over a trailing session window."""
    inst_bars = [b for b in bars if b.instrument_id == instrument_id]
    if not inst_bars:
        return Decimal("0.0")

    recent_bars = inst_bars[-window:]
    total_vol = sum((b.volume for b in recent_bars), Decimal("0.0"))
    return (total_vol / Decimal(len(recent_bars))).quantize(Decimal("0.0001"))
