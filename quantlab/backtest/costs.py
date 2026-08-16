"""Transaction costs, commissions, and slippage models."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from quantlab.domain.orders import OrderSide


@dataclass(frozen=True, slots=True)
class CostBreakdown:
    """Itemized transaction cost breakdown."""

    commission: Decimal
    slippage: Decimal
    market_impact: Decimal
    total_cost: Decimal


class SlippageModel:
    """Calculates adverse execution price slippage in basis points."""

    def __init__(self, slippage_bps: Decimal = Decimal("5.0")) -> None:
        self._slippage_bps = slippage_bps

    @property
    def slippage_bps(self) -> Decimal:
        return self._slippage_bps

    def execute_price(self, reference_price: Decimal, side: OrderSide) -> tuple[Decimal, Decimal]:
        """Returns (slipped_price, per_share_slippage_cost)."""
        slip_pct = self._slippage_bps / Decimal("10000.0")
        slip_amount = (reference_price * slip_pct).quantize(Decimal("0.0001"))

        if side == OrderSide.BUY:
            slipped_price = reference_price + slip_amount
        else:
            slipped_price = reference_price - slip_amount

        return slipped_price.quantize(Decimal("0.0001")), slip_amount


class FeeModel:
    """Calculates broker commissions and exchange fees."""

    def __init__(
        self,
        commission_per_share: Decimal = Decimal("0.0"),
        min_commission: Decimal = Decimal("0.0"),
    ) -> None:
        self._commission_per_share = commission_per_share
        self._min_commission = min_commission

    def calculate_fees(self, quantity: Decimal, price: Decimal) -> Decimal:
        raw_fee = quantity * self._commission_per_share
        fee = max(raw_fee, self._min_commission)
        return fee.quantize(Decimal("0.01"))
