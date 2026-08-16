"""Tests for OrderPlanner generating integer orders."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from quantlab.domain.identity import InstrumentId
from quantlab.domain.orders import OrderSide
from quantlab.domain.portfolio import PortfolioSnapshot, Position, TargetPortfolio, TargetPosition
from quantlab.portfolio.orders import OrderPlanner, OrderPlanningSpec


def test_order_planner_sells_before_buys() -> None:
    now = datetime(2026, 1, 1, 16, 0, tzinfo=UTC)
    inst_a = InstrumentId(uuid.UUID(int=1))
    inst_b = InstrumentId(uuid.UUID(int=2))

    prices = {inst_a: Decimal("100.0"), inst_b: Decimal("50.0")}
    total_equity = Decimal("100000.0")

    # Current portfolio holds 500 shares of A ($50,000) and $50,000 cash
    current = PortfolioSnapshot(
        portfolio_id="PORT-001",
        as_of=now,
        cash=Decimal("50000.0"),
        positions=(
            Position(
                instrument_id=inst_a,
                quantity=Decimal("500.0"),
                cost_basis=Decimal("100.0"),
                market_value=Decimal("50000.0"),
            ),
        ),
    )

    # Target: 0% A (sell all), 50% B ($50,000 = 1000 shares)
    target = TargetPortfolio(
        portfolio_id="PORT-001",
        decision_time=now,
        positions=(
            TargetPosition(
                instrument_id=inst_b, target_weight=Decimal("0.50"), target_quantity=None
            ),
        ),
        source_alpha_snapshot_id="hash-123",
    )

    planner = OrderPlanner()
    plan = planner.plan(current, target, prices, total_equity)

    assert len(plan.orders) == 2
    # Order 0 must be SELL A
    assert plan.orders[0].instrument_id == inst_a
    assert plan.orders[0].side == OrderSide.SELL
    assert plan.orders[0].quantity == Decimal("500.0")

    # Order 1 must be BUY B
    assert plan.orders[1].instrument_id == inst_b
    assert plan.orders[1].side == OrderSide.BUY
    assert plan.orders[1].quantity == Decimal("1000.0")


def test_order_planner_no_trade_band() -> None:
    now = datetime(2026, 1, 1, 16, 0, tzinfo=UTC)
    inst_a = InstrumentId(uuid.UUID(int=1))

    prices = {inst_a: Decimal("100.0")}
    total_equity = Decimal("100000.0")

    # Current holding: 500 shares = 50.0%
    current = PortfolioSnapshot(
        portfolio_id="PORT-001",
        as_of=now,
        cash=Decimal("50000.0"),
        positions=(
            Position(
                instrument_id=inst_a,
                quantity=Decimal("500.0"),
                cost_basis=Decimal("100.0"),
                market_value=Decimal("50000.0"),
            ),
        ),
    )

    # Target: 50.2% (delta = 0.2%, below 0.5% band)
    target = TargetPortfolio(
        portfolio_id="PORT-001",
        decision_time=now,
        positions=(
            TargetPosition(
                instrument_id=inst_a, target_weight=Decimal("0.502"), target_quantity=None
            ),
        ),
        source_alpha_snapshot_id="hash-123",
    )

    planner = OrderPlanner(OrderPlanningSpec(no_trade_band_pct=Decimal("0.005")))
    plan = planner.plan(current, target, prices, total_equity)

    # No orders generated because within no-trade band
    assert len(plan.orders) == 0
