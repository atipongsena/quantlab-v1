"""Volume participation and market impact models."""

from __future__ import annotations

import math
from decimal import Decimal


class VolumeParticipationModel:
    """Limits order fill size to a maximum fraction of bar trading volume."""

    def __init__(self, max_participation_pct: Decimal = Decimal("0.10")) -> None:
        self._max_participation_pct = max_participation_pct

    def max_executable_quantity(self, bar_volume: Decimal) -> Decimal:
        if bar_volume <= Decimal("0.0"):
            return Decimal("0.0")
        max_shares = math.floor(bar_volume * self._max_participation_pct)
        return Decimal(str(max_shares))
