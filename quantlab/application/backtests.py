"""Application service for orchestrating authoritative backtests and emitting artifacts."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime, time
from decimal import Decimal
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from quantlab.analytics.benchmark import BenchmarkComparison, compare_to_benchmark
from quantlab.backtest.engine import BacktestEngine
from quantlab.backtest.result import BacktestResult, BacktestSpec
from quantlab.data.corporate_actions import SqlCorporateActionStore
from quantlab.data.datasets import DatasetUniverseResolver
from quantlab.data.fundamentals import SqlFundamentalStore
from quantlab.data.macro import SqlMacroStore
from quantlab.data.market_bars import MarketBarStore
from quantlab.data.pit_facade import PointInTimeDataFacade
from quantlab.domain.corporate_actions import CorporateAction
from quantlab.domain.identity import InstrumentId
from quantlab.domain.market import BarPriceSemantic, MarketBar
from quantlab.factors.catalog import register_standard_factors
from quantlab.factors.composites import CompositeBuilder, CompositeSpec
from quantlab.factors.contracts import FactorContext, FactorSnapshot
from quantlab.factors.registry import FactorRegistry
from quantlab.infrastructure.analytical_store import LocalAnalyticalStore
from quantlab.infrastructure.db import DatabaseConfig, DatabaseEngine
from quantlab.infrastructure.instrument_repository import SqlInstrumentRepository
from quantlab.portfolio.construction import PortfolioSpec
from quantlab.portfolio.risk import RiskSpec
from quantlab.universe.membership import UniverseEngine


@dataclass
class PreparedBacktest:
    """A loaded study that can be re-run under different assumptions.

    Everything expensive - bars, corporate actions, the trading calendar, and the
    point-in-time component factor snapshots - is held here so a robustness sweep costs
    one signal computation rather than one per variant.
    """

    service: BacktestService
    spec: BacktestSpec
    config: Mapping[str, object]
    dataset_id: str
    instruments: tuple[InstrumentId, ...]
    sectors: Mapping[InstrumentId, str]
    dataset_sessions: tuple[date, ...]
    bars_by_session: Mapping[date, Mapping[InstrumentId, MarketBar]]
    actions_by_session: Mapping[date, Sequence[CorporateAction]]
    composite_spec: CompositeSpec
    registry: FactorRegistry
    pit_facade: PointInTimeDataFacade
    universes: DatasetUniverseResolver
    _component_cache: dict[date, dict[str, FactorSnapshot]] = field(default_factory=dict)

    def _components(self, session: date) -> dict[str, FactorSnapshot]:
        cached = self._component_cache.get(session)
        if cached is not None:
            return cached

        context = FactorContext(
            dataset_id=self.dataset_id,
            session=session,
            as_of=datetime.combine(session, time(21, 0), tzinfo=UTC),
            pit_data=self.pit_facade,
            universe=self.instruments,
        )
        calculators = []
        for factor_id in self.composite_spec.factor_weights:
            calculator = self.registry.get(factor_id)
            if calculator is None:
                raise KeyError(f"Factor '{factor_id}' is not registered")
            calculators.append((factor_id, calculator))

        # Longest lookback first so the shorter windows are served from the facade's
        # per-as-of price cache rather than re-adjusting the same bars.
        calculators.sort(key=lambda item: item[1].definition.lookback_sessions, reverse=True)

        components: dict[str, FactorSnapshot] = {
            factor_id: calculator.compute(context) for factor_id, calculator in calculators
        }
        self._component_cache[session] = components
        return components

    def run(
        self,
        target_size: int | None = None,
        slippage_bps: Decimal | None = None,
        commission_per_share: Decimal | None = None,
        drop_factors: Sequence[str] = (),
    ) -> BacktestResult:
        """Run the study, optionally with one assumption changed.

        ``drop_factors`` removes sleeves from the composite and renormalizes the rest,
        which is what a factor ablation is: how much of the result survives without a
        given signal.
        """
        spec = self.spec
        portfolio_spec = spec.portfolio_spec
        if target_size is not None:
            portfolio_spec = replace(
                portfolio_spec,
                target_size=target_size,
                buffer_size=max(target_size + 10, portfolio_spec.buffer_size),
            )

        run_spec = replace(
            spec,
            portfolio_spec=portfolio_spec,
            slippage_bps=spec.slippage_bps if slippage_bps is None else slippage_bps,
            commission_per_share=(
                spec.commission_per_share if commission_per_share is None else commission_per_share
            ),
        )

        composite_spec = self.composite_spec
        if drop_factors:
            remaining = {
                factor_id: weight
                for factor_id, weight in composite_spec.factor_weights.items()
                if factor_id not in drop_factors
            }
            if not remaining:
                raise ValueError("Ablation removed every factor from the composite")
            total = sum(remaining.values())
            composite_spec = replace(
                composite_spec,
                factor_weights={k: v / total for k, v in remaining.items()},
            )

        keep = set(composite_spec.factor_weights)

        def alpha_provider(session: date) -> FactorSnapshot:
            components = {
                factor_id: snapshot
                for factor_id, snapshot in self._components(session).items()
                if factor_id in keep
            }
            return CompositeBuilder.build(components, composite_spec)

        engine = BacktestEngine(
            bars_provider=lambda session: self.bars_by_session.get(session, {}),
            corporate_actions_provider=lambda session: self.actions_by_session.get(session, ()),
            alpha_provider=alpha_provider,
            sectors_provider=lambda _: self.sectors,
            universe_provider=lambda _: list(self.instruments),
            sessions_provider=lambda first, last: [
                s for s in self.dataset_sessions if first <= s <= last
            ],
        )
        return engine.run(run_spec)


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
        self.last_benchmark_comparison: BenchmarkComparison | None = None

    def _create_pit_facade(self, dataset_id: str) -> PointInTimeDataFacade:
        inst_repo = SqlInstrumentRepository(self._db_engine)
        bar_store = MarketBarStore(self._analytical_store, MarketBarStore.namespace_for(dataset_id))
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

    def _compare_to_benchmark(
        self,
        result: BacktestResult,
        dataset_id: str,
        benchmark_symbol: str,
        pit_facade: PointInTimeDataFacade,
        universes: DatasetUniverseResolver,
    ) -> BenchmarkComparison | None:
        """Align the strategy's daily returns with a buy-and-hold benchmark.

        The benchmark is read on total-return adjusted prices because a buy-and-hold
        holder receives the dividends; comparing against a price-only index would hand
        the strategy roughly two points a year of free outperformance.
        """
        member = universes.benchmark(dataset_id, benchmark_symbol)
        if member is None or not result.daily_returns:
            return None

        sessions = sorted(result.daily_returns)
        as_of = datetime.combine(sessions[-1], time(23, 59), tzinfo=UTC)
        bars = pit_facade.get_market_bars(
            instrument_id=member.instrument_id,
            start_date=sessions[0],
            end_date=sessions[-1],
            as_of=as_of,
            adjusted=True,
        )
        closes = {bar.session: float(bar.close) for bar in bars}

        strategy_returns: list[float] = []
        benchmark_returns: list[float] = []
        previous_close: float | None = None
        for session in sessions:
            close = closes.get(session)
            if close is None or close <= 0:
                continue
            if previous_close is not None:
                strategy_returns.append(result.daily_returns[session])
                benchmark_returns.append(close / previous_close - 1.0)
            previous_close = close

        if len(strategy_returns) < 2:
            return None
        return compare_to_benchmark(strategy_returns, benchmark_returns, member.symbol)

    def prepare(
        self,
        strategy_config_path: str | Path,
        dataset_id: str = "DATASET-v001",
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> PreparedBacktest:
        """Load everything a run needs, so variants of the same study share the work.

        Computing point-in-time factor snapshots dominates the runtime of a multi-decade
        backtest. A robustness sweep changes portfolio size or cost assumptions, not the
        signal, so the snapshots are computed once here and reused across every variant.
        Factor ablations reuse them too: dropping a sleeve is a recombination of
        component snapshots, not a recomputation.
        """
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

        # Execution universe is the dataset's equities. ETFs stay out of the ranked
        # cross-section (spec 2.7) and are only used as benchmarks.
        universes = DatasetUniverseResolver(self._analytical_store)
        members = universes.equities(dataset_id)
        if not members:
            raise ValueError(f"Dataset '{dataset_id}' contains no equity instruments")
        all_instruments = [m.instrument_id for m in members]
        sector_by_instrument = {m.instrument_id: m.sector for m in members}

        pit_facade = self._create_pit_facade(dataset_id)
        bar_store = MarketBarStore(self._analytical_store, MarketBarStore.namespace_for(dataset_id))

        # The dataset's own sessions are the calendar. Ad-hoc closures are in the data.
        session_universe: set[date] = set()
        for inst_id in all_instruments:
            session_universe.update(bar_store.list_sessions(inst_id, BarPriceSemantic.RAW))
        dataset_sessions = sorted(session_universe)
        if not dataset_sessions:
            raise ValueError(f"Dataset '{dataset_id}' holds no market bars")

        cfg_start = cfg_data.get("start_date")
        cfg_end = cfg_data.get("end_date")
        start_s = start_date or (date.fromisoformat(str(cfg_start)) if cfg_start else None)
        end_s = end_date or (date.fromisoformat(str(cfg_end)) if cfg_end else None)
        start_s = start_s or dataset_sessions[0]
        end_s = end_s or dataset_sessions[-1]

        exec_cfg = cfg_data.get("execution", {})
        spec = BacktestSpec(
            strategy_id=strategy_id,
            dataset_id=dataset_id,
            start_session=start_s,
            end_session=end_s,
            initial_cash=Decimal(str(cfg_data.get("initial_cash", "1000000.00"))),
            portfolio_spec=portfolio_spec,
            risk_spec=risk_spec,
            slippage_bps=Decimal(str(exec_cfg.get("slippage_bps", "5.0"))),
            commission_per_share=Decimal(str(exec_cfg.get("commission_per_share", "0.005"))),
        )

        # Execution and accounting run on raw as-traded prices; dividends reach the
        # portfolio as cash through the corporate-action path, never folded into price.
        bars_by_session: dict[date, dict[InstrumentId, MarketBar]] = {}
        for inst_id in all_instruments:
            for bar in bar_store.get_bars(inst_id, start_s, end_s, BarPriceSemantic.RAW):
                bars_by_session.setdefault(bar.session, {})[inst_id] = bar

        actions_by_session: dict[date, list[CorporateAction]] = {}
        action_store = SqlCorporateActionStore(self._db_engine)
        for inst_id in all_instruments:
            for action in action_store.get_actions(inst_id, start_s, end_s):
                actions_by_session.setdefault(action.effective_at, []).append(action)

        registry = register_standard_factors(FactorRegistry.global_instance())
        composite_cfg_path = self._base_dir / "configs" / "factors" / f"{composite_id}.yaml"
        if not composite_cfg_path.exists():
            composite_cfg_path = self._base_dir / "configs" / "factors" / "composite-v1.yaml"
        with open(composite_cfg_path, encoding="utf-8") as f:
            composite_cfg = yaml.safe_load(f) or {}
        composite_spec = CompositeSpec(
            composite_id=composite_cfg.get("composite_id", composite_id),
            version=composite_cfg.get("version", "v1"),
            factor_weights=composite_cfg["weights"],
            min_weight_fraction=composite_cfg.get("min_weight_fraction", 0.5),
            normalize_method=composite_cfg.get("normalize_method", "zscore"),
            metadata=composite_cfg,
        )

        return PreparedBacktest(
            service=self,
            spec=spec,
            config=cfg_data,
            dataset_id=dataset_id,
            instruments=tuple(all_instruments),
            sectors=sector_by_instrument,
            dataset_sessions=tuple(dataset_sessions),
            bars_by_session=bars_by_session,
            actions_by_session=actions_by_session,
            composite_spec=composite_spec,
            registry=registry,
            pit_facade=pit_facade,
            universes=universes,
        )

    def run_backtest(
        self,
        strategy_config_path: str | Path,
        dataset_id: str = "DATASET-v001",
        start_date: date | None = None,
        end_date: date | None = None,
        output_dir: Path | None = None,
    ) -> BacktestResult:
        prepared = self.prepare(strategy_config_path, dataset_id, start_date, end_date)
        result = prepared.run()
        spec = prepared.spec

        comparison = self._compare_to_benchmark(
            result=result,
            dataset_id=dataset_id,
            benchmark_symbol=str(prepared.config.get("benchmark", "SPY")),
            pit_facade=prepared.pit_facade,
            universes=prepared.universes,
        )
        self.last_benchmark_comparison = comparison

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
            "benchmark": comparison.as_dict() if comparison else None,
            "equity": {d.isoformat(): str(eq) for d, eq in result.equity_series.items()},
            "content_hash": result.content_hash,
            "status": "PASS",
        }
        with open(out_dir / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        return result
