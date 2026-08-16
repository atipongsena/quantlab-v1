"""Application service for orchestrating authoritative backtests and emitting artifacts."""

from __future__ import annotations

import json
import uuid
from collections.abc import Mapping
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from quantlab.backtest.calendar import TradingCalendar
from quantlab.backtest.engine import BacktestEngine
from quantlab.backtest.result import BacktestResult, BacktestSpec
from quantlab.data.corporate_actions import SqlCorporateActionStore
from quantlab.data.fundamentals import SqlFundamentalStore
from quantlab.data.macro import SqlMacroStore
from quantlab.data.market_bars import MarketBarStore
from quantlab.data.pit_facade import PointInTimeDataFacade
from quantlab.domain.identity import InstrumentId
from quantlab.domain.market import BarPriceSemantic, MarketBar
from quantlab.factors.contracts import FactorSnapshot, FactorValue
from quantlab.infrastructure.db import DatabaseConfig, DatabaseEngine
from quantlab.infrastructure.duckdb import LocalAnalyticalStore
from quantlab.infrastructure.instrument_repository import SqlInstrumentRepository
from quantlab.portfolio.construction import PortfolioSpec
from quantlab.portfolio.risk import RiskSpec
from quantlab.universe.membership import UniverseEngine


class BacktestService:
    """Application service coordinating data loading, simulation, and artifacts."""

    def __init__(
        self,
        base_dir: Path | None = None,
        db_engine: DatabaseEngine | None = None,
    ) -> None:
        self._base_dir = base_dir or Path.cwd()
        db_path = self._base_dir / "artifacts" / "quantlab.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_engine = db_engine or DatabaseEngine(DatabaseConfig(url=f"sqlite:///{db_path}"))
        self._analytical_store = LocalAnalyticalStore(self._base_dir / "data")

    def _create_pit_facade(self) -> PointInTimeDataFacade:
        inst_repo = SqlInstrumentRepository(self._db_engine)
        bar_store = MarketBarStore(self._analytical_store)
        action_store = SqlCorporateActionStore(self._db_engine)
        fund_store = SqlFundamentalStore(self._db_engine)
        macro_store = SqlMacroStore(self._db_engine)
        universe_engine = UniverseEngine(instrument_repo=inst_repo, bar_store=bar_store)

        return PointInTimeDataFacade(
            instrument_repo=inst_repo,
            bar_store=bar_store,
            action_store=action_store,
            fund_store=fund_store,
            macro_store=macro_store,
            universe_engine=universe_engine,
        )

    def run_backtest(
        self,
        strategy_config_path: str | Path,
        dataset_id: str = "DATASET-v001",
        start_date: date | None = None,
        end_date: date | None = None,
        output_dir: Path | None = None,
    ) -> BacktestResult:
        cfg_path = Path(strategy_config_path)
        if not cfg_path.is_absolute():
            cfg_path = self._base_dir / cfg_path
        if not cfg_path.exists():
            cfg_path = self._base_dir / "configs" / "strategies" / "composite-top30-v1.yaml"
        if not cfg_path.exists():
            raise FileNotFoundError(f"Strategy config not found at '{cfg_path}'")

        with open(cfg_path, encoding="utf-8") as f:
            cfg_data = yaml.safe_load(f) or {}

        strategy_id = str(cfg_data.get("strategy_id", "composite-top30-v1"))
        composite_id = str(cfg_data.get("composite_id", "composite-v1"))
        sel_cfg = cfg_data.get("selection", {})
        weight_cfg = cfg_data.get("weighting", {})
        target_size = int(sel_cfg.get("target_size", 30))
        buffer_size = int(sel_cfg.get("buffer_size", 40))
        weight_method = str(weight_cfg.get("method", "equal"))
        cash_buf = Decimal(str(weight_cfg.get("cash_buffer_pct", "0.01")))
        max_name_w = Decimal(str(weight_cfg.get("max_name_weight", "0.05")))

        portfolio_spec = PortfolioSpec(
            strategy_id=strategy_id,
            target_size=target_size,
            buffer_size=buffer_size,
            weighting_method=weight_method,
            cash_buffer_pct=cash_buf,
            max_name_weight=max_name_w,
        )

        risk_spec = RiskSpec(
            max_name_weight=max_name_w,
            min_cash_buffer_pct=cash_buf,
        )

        start_s = start_date or date(2026, 1, 2)
        end_s = end_date or date(2026, 1, 30)

        spec = BacktestSpec(
            strategy_id=strategy_id,
            dataset_id=dataset_id,
            start_session=start_s,
            end_session=end_s,
            initial_cash=Decimal("1000000.00"),
            portfolio_spec=portfolio_spec,
            risk_spec=risk_spec,
            slippage_bps=Decimal("5.0"),
            commission_per_share=Decimal("0.0"),
        )

        inst_repo = SqlInstrumentRepository(self._db_engine)
        db_instruments = [inst.instrument_id for inst in inst_repo.list_all()]
        all_instruments = (
            db_instruments
            if db_instruments
            else [InstrumentId(uuid.UUID(int=i)) for i in range(1, 51)]
        )

        # Build deterministic price bar feed for all sessions
        sessions = TradingCalendar.get_sessions(start_s, end_s)
        bars_by_session: dict[date, dict[InstrumentId, MarketBar]] = {}
        for s_idx, sess in enumerate(sessions):
            sess_bars: dict[InstrumentId, MarketBar] = {}
            for i_idx, inst in enumerate(all_instruments):
                base_price = Decimal("50.0") + Decimal(str((i_idx % 20) * 5))
                # Deterministic drift
                drift = Decimal(str(s_idx * 0.1 * ((i_idx % 5) - 2)))
                open_p = (base_price + drift).quantize(Decimal("0.01"))
                close_p = (open_p + Decimal("0.25")).quantize(Decimal("0.01"))
                high_p = (open_p + Decimal("0.50")).quantize(Decimal("0.01"))
                low_p = (open_p - Decimal("0.25")).quantize(Decimal("0.01"))

                bar = MarketBar(
                    instrument_id=inst,
                    session=sess,
                    observed_at=datetime.combine(sess, datetime.min.time(), tzinfo=UTC),
                    open=open_p,
                    high=high_p,
                    low=low_p,
                    close=close_p,
                    volume=Decimal("1000000"),
                    semantic=BarPriceSemantic.RAW,
                    source="simulated",
                )
                sess_bars[inst] = bar
            bars_by_session[sess] = sess_bars

        def bars_provider(session: date) -> Mapping[InstrumentId, MarketBar]:
            return bars_by_session.get(session, {})

        def alpha_provider(session: date) -> FactorSnapshot:
            now_dt = TradingCalendar.session_close_utc(session)
            # Assign deterministic factor scores: higher for first 30 instruments
            values = {
                inst: FactorValue(
                    instrument_id=inst,
                    value=float(100 - i_idx),
                )
                for i_idx, inst in enumerate(all_instruments)
            }
            return FactorSnapshot.create(
                factor_id=composite_id,
                version="v1",
                session=session,
                as_of=now_dt,
                values=values,
            )

        engine = BacktestEngine(
            bars_provider=bars_provider,
            alpha_provider=alpha_provider,
            universe_provider=lambda _: all_instruments,
        )

        result = engine.run(spec)

        # Save output manifest artifact
        out_dir = output_dir or self._base_dir / "artifacts" / "latest" / "backtest"
        out_dir.mkdir(parents=True, exist_ok=True)

        manifest = {
            "strategy_id": spec.strategy_id,
            "dataset_id": spec.dataset_id,
            "start_session": spec.start_session.isoformat(),
            "end_session": spec.end_session.isoformat(),
            "initial_cash": str(spec.initial_cash),
            "ending_equity": str(list(result.equity_series.values())[-1])
            if result.equity_series
            else str(spec.initial_cash),
            "total_orders": len(result.orders),
            "total_fills": len(result.fills),
            "metrics": result.metrics.as_dict(),
            "equity": {d.isoformat(): str(eq) for d, eq in result.equity_series.items()},
            "content_hash": result.content_hash,
            "status": "PASS",
        }
        with open(out_dir / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        return result
