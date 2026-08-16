"""Property tests for portfolio construction."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from quantlab.domain.identity import InstrumentId
from quantlab.factors.snapshots import build_factor_snapshot
from quantlab.portfolio.construction import ConstructionRequest, PortfolioConstructor, PortfolioSpec


def test_portfolio_construction_end_to_end() -> None:
    instruments = [InstrumentId(uuid.UUID(int=i + 1)) for i in range(60)]
    now = datetime(2026, 1, 1, 16, 0, tzinfo=UTC)

    raw_scores = {inst: float(60 - i) for i, inst in enumerate(instruments)}
    snapshot = build_factor_snapshot(
        factor_id="composite-v1",
        version="v1",
        session=date(2026, 1, 1),
        as_of=now,
        raw_values=raw_scores,
    )

    spec = PortfolioSpec(
        strategy_id="composite-top30-v1",
        target_size=30,
        buffer_size=40,
        weighting_method="equal",
        cash_buffer_pct=Decimal("0.01"),
        max_name_weight=Decimal("0.05"),
    )

    request = ConstructionRequest(
        portfolio_id="PORT-001",
        decision_time=now,
        alpha_snapshot=snapshot,
        universe=instruments,
        current_portfolio=None,
        spec=spec,
    )

    target_portfolio = PortfolioConstructor.construct(request)

    assert target_portfolio.portfolio_id == "PORT-001"
    assert len(target_portfolio.positions) == 30
    assert target_portfolio.source_alpha_snapshot_id == snapshot.content_hash

    total_weight = sum(p.target_weight for p in target_portfolio.positions)
    assert total_weight == Decimal("0.99")
    for pos in target_portfolio.positions:
        assert pos.target_weight <= Decimal("0.05")
        assert pos.target_weight > Decimal("0.0")
