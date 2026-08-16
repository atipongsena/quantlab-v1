"""Deterministic order planning from target portfolios and market state."""

from __future__ import annotations

import math
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from quantlab.domain.identity import InstrumentId
from quantlab.domain.orders import Order, OrderSide, OrderState, OrderType
from quantlab.domain.portfolio import PortfolioSnapshot, TargetPortfolio


@dataclass(frozen=True, slots=True)
class OrderPlanningSpec:
    """Configuration for translation of target weights into executable orders."""

    no_trade_band_pct: Decimal = Decimal("0.005")
    min_trade_dollar: Decimal = Decimal("100.0")
    max_adv_participation: Decimal = Decimal("0.10")


@dataclass(frozen=True, slots=True)
class OrderPlan:
    """Complete, auditable plan of executable orders."""

    decision_time: datetime
    orders: tuple[Order, ...]
    total_buy_dollars: Decimal
    total_sell_dollars: Decimal
    turnover: Decimal
    diagnostics: Mapping[str, object] = field(default_factory=dict)


class OrderPlanner:
    """Generates discrete, integer-sized market orders from target portfolios."""

    def __init__(self, spec: OrderPlanningSpec | None = None) -> None:
        self._spec = spec or OrderPlanningSpec()

    def plan(
        self,
        current_portfolio: PortfolioSnapshot | None,
        approved_target: TargetPortfolio,
        prices: Mapping[InstrumentId, Decimal],
        total_equity: Decimal,
        adv_shares: Mapping[InstrumentId, Decimal] | None = None,
    ) -> OrderPlan:
        if total_equity <= Decimal("0.0"):
            return OrderPlan(
                decision_time=approved_target.decision_time,
                orders=(),
                total_buy_dollars=Decimal("0.0"),
                total_sell_dollars=Decimal("0.0"),
                turnover=Decimal("0.0"),
            )

        current_quantities: dict[InstrumentId, Decimal] = {}
        if current_portfolio is not None:
            current_quantities = {
                pos.instrument_id: pos.quantity for pos in current_portfolio.positions
            }

        target_weights = {p.instrument_id: p.target_weight for p in approved_target.positions}
        all_instruments = set(current_quantities.keys()) | set(target_weights.keys())

        sell_orders: list[Order] = []
        buy_orders: list[Order] = []
        total_buy_dollars = Decimal("0.0")
        total_sell_dollars = Decimal("0.0")

        # Process each instrument deterministically by UUID string
        for inst in sorted(all_instruments, key=lambda i: str(i.value)):
            price = prices.get(inst)
            if price is None or price <= Decimal("0.0"):
                continue

            curr_qty = current_quantities.get(inst, Decimal("0.0"))
            curr_weight = (curr_qty * price) / total_equity
            target_weight = target_weights.get(inst, Decimal("0.0"))

            # Calculate target integer shares: floor(target_equity * target_weight / price)
            target_dollars = total_equity * target_weight
            target_qty = Decimal(str(math.floor(target_dollars / price)))

            delta_qty = target_qty - curr_qty
            delta_weight = abs(target_weight - curr_weight)

            # 1. No-trade band: skip small adjustments for existing active positions
            if (
                curr_qty > Decimal("0.0")
                and target_weight > Decimal("0.0")
                and delta_weight < self._spec.no_trade_band_pct
            ):
                continue

            trade_dollars = abs(delta_qty * price)
            # 2. Minimum trade dollar constraint (unless exiting completely)
            if target_weight > Decimal("0.0") and trade_dollars < self._spec.min_trade_dollar:
                continue

            if delta_qty == Decimal("0.0"):
                continue

            # Check ADV participation cap
            adv_cap = None
            if adv_shares and inst in adv_shares:
                adv = adv_shares[inst]
                if adv > Decimal("0.0"):
                    adv_cap = Decimal(str(math.floor(adv * self._spec.max_adv_participation)))

            if delta_qty < Decimal("0.0"):
                qty_to_sell = abs(delta_qty)
                if adv_cap is not None and qty_to_sell > adv_cap and adv_cap > Decimal("0.0"):
                    qty_to_sell = adv_cap

                order = Order(
                    order_id=f"ORD-{uuid.uuid4().hex[:12]}",
                    instrument_id=inst,
                    side=OrderSide.SELL,
                    order_type=OrderType.MARKET,
                    quantity=qty_to_sell,
                    state=OrderState.CREATED,
                    created_at=approved_target.decision_time,
                )
                sell_orders.append(order)
                total_sell_dollars += qty_to_sell * price

            elif delta_qty > Decimal("0.0"):
                qty_to_buy = delta_qty
                if adv_cap is not None and qty_to_buy > adv_cap and adv_cap > Decimal("0.0"):
                    qty_to_buy = adv_cap

                order = Order(
                    order_id=f"ORD-{uuid.uuid4().hex[:12]}",
                    instrument_id=inst,
                    side=OrderSide.BUY,
                    order_type=OrderType.MARKET,
                    quantity=qty_to_buy,
                    state=OrderState.CREATED,
                    created_at=approved_target.decision_time,
                )
                buy_orders.append(order)
                total_buy_dollars += qty_to_buy * price

        # Order sequencing: Sells first, then Buys
        all_orders = tuple(sell_orders + buy_orders)
        turnover = (
            ((total_buy_dollars + total_sell_dollars) / (Decimal("2.0") * total_equity)).quantize(
                Decimal("0.0001")
            )
            if total_equity > Decimal("0.0")
            else Decimal("0.0")
        )

        return OrderPlan(
            decision_time=approved_target.decision_time,
            orders=all_orders,
            total_buy_dollars=total_buy_dollars.quantize(Decimal("0.01")),
            total_sell_dollars=total_sell_dollars.quantize(Decimal("0.01")),
            turnover=turnover,
        )
