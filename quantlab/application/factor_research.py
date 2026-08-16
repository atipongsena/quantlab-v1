"""Factor research and multi-factor composite application service."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, datetime, time
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from quantlab.data.corporate_actions import SqlCorporateActionStore
from quantlab.data.fundamentals import SqlFundamentalStore
from quantlab.data.macro import SqlMacroStore
from quantlab.data.market_bars import MarketBarStore
from quantlab.data.pit_facade import PointInTimeDataFacade
from quantlab.domain.identity import InstrumentId
from quantlab.domain.market import BarPriceSemantic
from quantlab.factors.catalog import register_standard_factors
from quantlab.factors.composites import CompositeBuilder, CompositeSpec
from quantlab.factors.contracts import FactorContext, FactorSnapshot
from quantlab.factors.evaluation import (
    EvaluationSpec,
    FactorEvaluator,
    FactorResearchResult,
    ForwardReturnView,
)
from quantlab.factors.registry import FactorRegistry
from quantlab.infrastructure.db import DatabaseConfig, DatabaseEngine
from quantlab.infrastructure.duckdb import LocalAnalyticalStore
from quantlab.infrastructure.instrument_repository import SqlInstrumentRepository
from quantlab.universe.membership import UniverseEngine


class FactorResearchService:
    """Service providing factor research workflows and multi-factor composite evaluation."""

    def __init__(
        self,
        base_dir: Path | None = None,
        db_engine: DatabaseEngine | None = None,
        registry: FactorRegistry | None = None,
    ) -> None:
        self._base_dir = Path(base_dir or Path.cwd())
        db_path = self._base_dir / "artifacts" / "quantlab.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_engine = db_engine or DatabaseEngine(DatabaseConfig(url=f"sqlite:///{db_path}"))
        self._analytical_store = LocalAnalyticalStore(self._base_dir / "data")
        self._registry = register_standard_factors(registry or FactorRegistry.global_instance())

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

    def list_factors(self) -> list[dict[str, object]]:
        """List all available factor definitions."""
        factors = self._registry.list_factors()
        return [
            {
                "factor_id": f.factor_id,
                "name": f.name,
                "category": f.category,
                "description": f.description,
                "formula": f.formula,
                "direction": f.direction,
                "lookback_sessions": f.lookback_sessions,
                "version": f.calculator_version,
            }
            for f in sorted(factors, key=lambda x: x.factor_id)
        ]

    def _get_universe(self, pit_facade: PointInTimeDataFacade) -> tuple[InstrumentId, ...]:
        """Fetch all instruments from repo."""
        repo = SqlInstrumentRepository(self._db_engine)
        instruments = repo.list_all()
        return tuple(inst.instrument_id for inst in instruments)

    def _build_forward_returns(
        self,
        pit_facade: PointInTimeDataFacade,
        universe: Sequence[InstrumentId],
        sessions: Sequence[date],
        horizons: tuple[int, ...] = (21, 63, 126, 252),
    ) -> ForwardReturnView:
        """Compute forward returns across specified horizons for all sessions."""
        if not sessions:
            return ForwardReturnView(returns={})

        start_date = sessions[0]
        end_date = sessions[-1]
        as_of_latest = datetime.combine(end_date, time(23, 59), tzinfo=UTC)

        # Collect adjusted close price series for all instruments
        inst_prices: dict[InstrumentId, dict[date, float]] = {}
        for inst_id in universe:
            bars = pit_facade.get_market_bars(
                instrument_id=inst_id,
                start_date=start_date,
                end_date=end_date,
                as_of=as_of_latest,
                adjusted=True,
            )
            inst_prices[inst_id] = {b.session: float(b.close) for b in bars}

        returns_map: dict[tuple[date, int], dict[InstrumentId, float]] = {}
        session_list = sorted(sessions)

        for i, sess in enumerate(session_list):
            for h in horizons:
                if i + h < len(session_list):
                    target_sess = session_list[i + h]
                    h_returns: dict[InstrumentId, float] = {}
                    for inst_id in universe:
                        p_map = inst_prices.get(inst_id, {})
                        p_start = p_map.get(sess)
                        p_end = p_map.get(target_sess)
                        if p_start is not None and p_end is not None and p_start > 0:
                            h_returns[inst_id] = (p_end / p_start) - 1.0
                    returns_map[(sess, h)] = h_returns

        return ForwardReturnView(returns=returns_map)

    def run_factor_research(
        self,
        factor_id: str,
        dataset_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
        spec: EvaluationSpec | None = None,
    ) -> FactorResearchResult:
        """Execute factor evaluation pipeline for a given factor on a dataset."""
        calc = self._registry.get(factor_id)
        if calc is None:
            raise KeyError(f"Factor '{factor_id}' is not registered")

        pit_facade = self._create_pit_facade()
        universe = self._get_universe(pit_facade)
        if not universe:
            raise ValueError(f"No instruments found in dataset '{dataset_id}'")

        # Discover trading sessions from market bars
        raw_bars = pit_facade._bar_store.get_bars(  # noqa: SLF001
            instrument_id=universe[0],
            start_date=start_date or date(2015, 1, 1),
            end_date=end_date or date(2025, 12, 31),
            semantic=BarPriceSemantic.RAW,
        )
        all_sessions = sorted({b.session for b in raw_bars})
        if not all_sessions:
            # Fallback mock session
            all_sessions = [start_date or date.today()]

        # Filter by start_date / end_date
        if start_date:
            all_sessions = [s for s in all_sessions if s >= start_date]
        if end_date:
            all_sessions = [s for s in all_sessions if s <= end_date]

        # Monthly sample sessions (at least every 21 sessions or month-ends) for evaluation
        # Sample every 21 trading sessions for clean rebalance IC
        sample_sessions = [all_sessions[i] for i in range(0, len(all_sessions), 21)]
        if not sample_sessions:
            sample_sessions = all_sessions

        # Compute factor snapshots for each session
        snapshots: list[FactorSnapshot] = []
        for sess in sample_sessions:
            as_of_sess = datetime.combine(sess, time(16, 0), tzinfo=UTC)
            context = FactorContext(
                dataset_id=dataset_id,
                session=sess,
                as_of=as_of_sess,
                pit_data=pit_facade,
                universe=universe,
            )
            snap = calc.compute(context)
            snapshots.append(snap)

        forward_returns = self._build_forward_returns(
            pit_facade=pit_facade,
            universe=universe,
            sessions=all_sessions,
        )

        evaluator = FactorEvaluator(spec or EvaluationSpec())
        return evaluator.evaluate(snapshots, forward_returns)

    def run_composite(
        self,
        composite_id: str,
        dataset_id: str,
        config_path: str | Path | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        spec: EvaluationSpec | None = None,
    ) -> FactorResearchResult:
        """Evaluate a multi-factor composite strategy."""
        cfg_file = (
            Path(config_path)
            if config_path
            else self._base_dir / "configs" / "factors" / f"{composite_id}.yaml"
        )
        if not cfg_file.exists():
            cfg_file = self._base_dir / "configs" / "factors" / "composite-v1.yaml"
        if not cfg_file.exists():
            raise FileNotFoundError(f"Composite config not found at '{cfg_file}'")

        with open(cfg_file, encoding="utf-8") as f:
            cfg_data = yaml.safe_load(f)

        comp_spec = CompositeSpec(
            composite_id=cfg_data.get("composite_id", composite_id),
            version=cfg_data.get("version", "v1"),
            factor_weights=cfg_data["weights"],
            min_weight_fraction=cfg_data.get("min_weight_fraction", 0.5),
            normalize_method=cfg_data.get("normalize_method", "zscore"),
            metadata=cfg_data,
        )

        pit_facade = self._create_pit_facade()
        universe = self._get_universe(pit_facade)
        if not universe:
            raise ValueError(f"No instruments found in dataset '{dataset_id}'")

        # Discover sessions
        raw_bars = pit_facade._bar_store.get_bars(  # noqa: SLF001
            instrument_id=universe[0],
            start_date=start_date or date(2015, 1, 1),
            end_date=end_date or date(2025, 12, 31),
            semantic=BarPriceSemantic.RAW,
        )
        all_sessions = sorted({b.session for b in raw_bars})
        if not all_sessions:
            all_sessions = [start_date or date.today()]

        if start_date:
            all_sessions = [s for s in all_sessions if s >= start_date]
        if end_date:
            all_sessions = [s for s in all_sessions if s <= end_date]

        sample_sessions = [all_sessions[i] for i in range(0, len(all_sessions), 21)]
        if not sample_sessions:
            sample_sessions = all_sessions

        # Compute composite snapshots
        composite_snapshots: list[FactorSnapshot] = []
        for sess in sample_sessions:
            as_of_sess = datetime.combine(sess, time(16, 0), tzinfo=UTC)
            context = FactorContext(
                dataset_id=dataset_id,
                session=sess,
                as_of=as_of_sess,
                pit_data=pit_facade,
                universe=universe,
            )

            # Compute underlying factor snapshots
            factor_snaps: dict[str, FactorSnapshot] = {}
            for fid in comp_spec.factor_weights:
                f_calc = self._registry.get(fid)
                if f_calc is None:
                    raise KeyError(f"Component factor '{fid}' is not registered")
                factor_snaps[fid] = f_calc.compute(context)

            comp_snap = CompositeBuilder.build(factor_snaps, comp_spec)
            composite_snapshots.append(comp_snap)

        forward_returns = self._build_forward_returns(
            pit_facade=pit_facade,
            universe=universe,
            sessions=all_sessions,
        )

        evaluator = FactorEvaluator(spec or EvaluationSpec())
        return evaluator.evaluate(composite_snapshots, forward_returns)
