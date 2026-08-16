"""Tests for capacity, liquidity, and ADV limits."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from quantlab.domain.identity import InstrumentId
from quantlab.domain.orders import OrderSide
from quantlab.domain.portfolio import TargetPortfolio, TargetPosition
from quantlab.portfolio.orders import OrderPlanner, OrderPlanningSpec


def test_adv_participation_cap() -> None:
    now = datetime(2026, 1, 1, 16, 0, tzinfo=UTC)
    inst = InstrumentId(uuid.UUID(int=1))

    prices = {inst: Decimal("10.0")}
    total_equity = Decimal("1000000.0")

    # Target: 50% = $500,000 = 50,000 shares
    target = TargetPortfolio(
        portfolio_id="PORT-001",
        decision_time=now,
        positions=(
            TargetPosition(instrument_id=inst, target_weight=Decimal("0.50"), target_quantity=None),
        ),
        source_alpha_snapshot_id="hash-123",
    )

    # ADV = 100,000 shares -> 10% cap = 10,000 shares
    adv_shares = {inst: Decimal("100000.0")}

    planner = OrderPlanner(OrderPlanningSpec(max_adv_participation=Decimal("0.10")))
    plan = planner.plan(None, target, prices, total_equity, adv_shares=adv_shares)

    assert len(plan.orders) == 1
    assert plan.orders[0].side == OrderSide.BUY
    assert plan.orders[0].quantity == Decimal("10000.0")
