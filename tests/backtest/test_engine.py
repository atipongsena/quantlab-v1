"""Tests for BacktestEngine event loop execution."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from quantlab.backtest.engine import BacktestEngine
from quantlab.backtest.result import BacktestSpec
from quantlab.domain.identity import InstrumentId
from quantlab.domain.market import BarPriceSemantic, MarketBar
from quantlab.factors.contracts import FactorSnapshot, FactorValue
from quantlab.portfolio.construction import PortfolioSpec


def test_backtest_engine_run_simulation() -> None:
    inst1 = InstrumentId(uuid.UUID(int=1))
    inst2 = InstrumentId(uuid.UUID(int=2))
    all_insts = [inst1, inst2]

    # Provider generating rising price bars across 3 sessions
    def bars_provider(session: date) -> dict[InstrumentId, MarketBar]:
        day_offset = (session - date(2026, 1, 2)).days
        base_p = Decimal(str(100 + day_offset * 2))
        return {
            inst: MarketBar(
                instrument_id=inst,
                session=session,
                observed_at=datetime.combine(session, datetime.min.time(), tzinfo=UTC),
                open=base_p,
                high=base_p + Decimal("2.0"),
                low=base_p - Decimal("1.0"),
                close=base_p + Decimal("1.0"),
                volume=Decimal("100000"),
                semantic=BarPriceSemantic.RAW,
                source="test",
            )
            for inst in all_insts
        }

    def alpha_provider(session: date) -> FactorSnapshot:
        return FactorSnapshot.create(
            factor_id="test-alpha",
            version="v1",
            session=session,
            as_of=datetime.combine(session, datetime.min.time(), tzinfo=UTC),
            values={
                inst1: FactorValue(inst1, 10.0),
                inst2: FactorValue(inst2, 5.0),
            },
        )

    spec = BacktestSpec(
        strategy_id="test-strat",
        dataset_id="DATASET-v001",
        start_session=date(2026, 1, 2),
        end_session=date(2026, 1, 6),
        initial_cash=Decimal("100000.00"),
        portfolio_spec=PortfolioSpec(strategy_id="test-strat", target_size=2, buffer_size=2),
    )

    engine = BacktestEngine(
        bars_provider=bars_provider,
        alpha_provider=alpha_provider,
        universe_provider=lambda _: all_insts,
    )

    result = engine.run(spec)

    assert result.spec.strategy_id == "test-strat"
    assert len(result.equity_series) > 0
    assert result.content_hash != ""
    assert isinstance(result.metrics.total_return, float)
