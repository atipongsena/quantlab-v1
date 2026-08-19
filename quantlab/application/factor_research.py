"""Factor research and multi-factor composite application service."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, datetime, time
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from quantlab.data.corporate_actions import SqlCorporateActionStore
from quantlab.data.datasets import DatasetMember, DatasetUniverseResolver
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
from quantlab.factors.transforms import rank_cross_section
from quantlab.infrastructure.analytical_store import LocalAnalyticalStore
from quantlab.infrastructure.db import DatabaseConfig, DatabaseEngine
from quantlab.infrastructure.instrument_repository import SqlInstrumentRepository
from quantlab.ml.contracts import MLDataset
from quantlab.ml.dataset import MLDatasetBuilder
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
        self._universes = DatasetUniverseResolver(self._analytical_store)

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

    def _get_universe(self, dataset_id: str) -> tuple[DatasetMember, ...]:
        """Resolve the cross-sectional equity universe published with a dataset."""
        members = self._universes.equities(dataset_id)
        if not members:
            raise ValueError(f"Dataset '{dataset_id}' contains no equity instruments")
        return members

    def _discover_sessions(
        self,
        dataset_id: str,
        universe: Sequence[InstrumentId],
        start_date: date | None,
        end_date: date | None,
    ) -> list[date]:
        """Union the trading calendar across the whole universe.

        Sampling one instrument is unsafe: the first name alphabetically may have listed
        late, been delisted early, or have gaps, which silently truncates the study.
        """
        bar_store = MarketBarStore(self._analytical_store, MarketBarStore.namespace_for(dataset_id))
        sessions: set[date] = set()
        for inst_id in universe:
            sessions.update(bar_store.list_sessions(inst_id, BarPriceSemantic.RAW))

        ordered = sorted(sessions)
        if start_date:
            ordered = [s for s in ordered if s >= start_date]
        if end_date:
            ordered = [s for s in ordered if s <= end_date]
        return ordered

    @staticmethod
    def _rebalance_sessions(sessions: Sequence[date], step: int = 21) -> list[date]:
        """Take a monthly rebalance grid anchored on the last session of each month.

        Spec 4.3 makes the monthly cross-section the observation unit, and anchoring on
        month-end keeps research aligned with the rebalance the backtest actually trades.
        """
        if not sessions:
            return []

        by_month: dict[tuple[int, int], date] = {}
        for session in sessions:
            by_month[(session.year, session.month)] = session
        month_ends = sorted(by_month.values())
        return month_ends if month_ends else list(sessions[::step])

    def _build_forward_returns(
        self,
        pit_facade: PointInTimeDataFacade,
        universe: Sequence[InstrumentId],
        all_sessions: Sequence[date],
        eval_sessions: Sequence[date],
        horizons: tuple[int, ...] = (21, 63, 126, 252),
    ) -> ForwardReturnView:
        """Build tradable forward returns for each evaluation session.

        Entry is the next session's open, not the close the signal was observed at
        (spec 4.4): a score computed from the close of session *t* cannot be filled at
        that same close. Exit is the open *h* sessions later, on total-return adjusted
        prices so dividends are not dropped from the research return.
        """
        if not all_sessions or not eval_sessions:
            return ForwardReturnView(returns={})

        start_date = all_sessions[0]
        end_date = all_sessions[-1]
        as_of_latest = datetime.combine(end_date, time(23, 59), tzinfo=UTC)

        inst_prices: dict[InstrumentId, dict[date, float]] = {}
        for inst_id in universe:
            bars = pit_facade.get_market_bars(
                instrument_id=inst_id,
                start_date=start_date,
                end_date=end_date,
                as_of=as_of_latest,
                adjusted=True,
            )
            inst_prices[inst_id] = {b.session: float(b.open) for b in bars}

        session_list = sorted(all_sessions)
        index_of = {s: i for i, s in enumerate(session_list)}

        returns_map: dict[tuple[date, int], dict[InstrumentId, float]] = {}
        for sess in eval_sessions:
            base = index_of.get(sess)
            if base is None:
                continue
            entry_idx = base + 1
            if entry_idx >= len(session_list):
                continue
            entry_sess = session_list[entry_idx]

            for h in horizons:
                exit_idx = entry_idx + h
                if exit_idx >= len(session_list):
                    continue
                exit_sess = session_list[exit_idx]

                h_returns: dict[InstrumentId, float] = {}
                for inst_id in universe:
                    p_map = inst_prices.get(inst_id, {})
                    p_start = p_map.get(entry_sess)
                    p_end = p_map.get(exit_sess)
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

        pit_facade = self._create_pit_facade(dataset_id)
        members = self._get_universe(dataset_id)
        universe = tuple(m.instrument_id for m in members)

        all_sessions = self._discover_sessions(dataset_id, universe, start_date, end_date)
        if not all_sessions:
            raise ValueError(f"Dataset '{dataset_id}' holds no market bars in the requested window")

        eval_sessions = self._rebalance_sessions(all_sessions)

        snapshots: list[FactorSnapshot] = []
        for sess in eval_sessions:
            as_of_sess = datetime.combine(sess, time(16, 0), tzinfo=UTC)
            context = FactorContext(
                dataset_id=dataset_id,
                session=sess,
                as_of=as_of_sess,
                pit_data=pit_facade,
                universe=universe,
            )
            snapshots.append(calc.compute(context))

        forward_returns = self._build_forward_returns(
            pit_facade=pit_facade,
            universe=universe,
            all_sessions=all_sessions,
            eval_sessions=eval_sessions,
        )

        evaluator = FactorEvaluator(spec or EvaluationSpec())
        return evaluator.evaluate(snapshots, forward_returns)

    def build_factor_panel(
        self,
        dataset_id: str,
        factor_ids: Sequence[str],
        start_date: date | None = None,
        end_date: date | None = None,
        label_horizon: int = 21,
    ) -> MLDataset:
        """Assemble the monthly cross-sectional panel the ML models train on.

        Features are point-in-time factor scores at each month-end close. The label is
        the cross-sectional rank of the tradable forward return over the next
        ``label_horizon`` sessions, mapped onto [-0.5, 0.5]. Ranking is the target
        because the models are asked to order names, not to forecast a return level
        (spec 4.1), and a rank label is immune to the handful of extreme moves that
        would otherwise dominate a squared-error fit.
        """
        pit_facade = self._create_pit_facade(dataset_id)
        members = self._get_universe(dataset_id)
        universe = tuple(m.instrument_id for m in members)

        all_sessions = self._discover_sessions(dataset_id, universe, start_date, end_date)
        if not all_sessions:
            raise ValueError(f"Dataset '{dataset_id}' holds no market bars in the requested window")
        eval_sessions = self._rebalance_sessions(all_sessions)

        calculators = []
        for factor_id in factor_ids:
            calc = self._registry.get(factor_id)
            if calc is None:
                raise KeyError(f"Factor '{factor_id}' is not registered")
            calculators.append((factor_id, calc))

        # Session outer, longest lookback first. All factors at one rebalance share the
        # same as-of instant, so the widest price window is read and adjusted once and
        # the shorter-lookback factors slice it out of the facade's cache instead of
        # re-adjusting the same bars.
        calculators.sort(key=lambda item: item[1].definition.lookback_sessions, reverse=True)

        snapshots_by_factor: dict[str, dict[date, FactorSnapshot]] = {
            factor_id: {} for factor_id, _ in calculators
        }
        for sess in eval_sessions:
            context = FactorContext(
                dataset_id=dataset_id,
                session=sess,
                as_of=datetime.combine(sess, time(16, 0), tzinfo=UTC),
                pit_data=pit_facade,
                universe=universe,
            )
            for factor_id, calc in calculators:
                snapshots_by_factor[factor_id][sess] = calc.compute(context)

        forward_returns = self._build_forward_returns(
            pit_facade=pit_facade,
            universe=universe,
            all_sessions=all_sessions,
            eval_sessions=eval_sessions,
            horizons=(label_horizon,),
        )

        labels_by_session: dict[date, dict[InstrumentId, float]] = {}
        for sess in eval_sessions:
            returns = forward_returns.get_returns(sess, label_horizon)
            if len(returns) < 3:
                continue
            ranks = rank_cross_section(dict(returns), normalize=True)
            labels_by_session[sess] = {inst: value - 0.5 for inst, value in ranks.items()}

        return MLDatasetBuilder.build(
            dataset_id=dataset_id,
            factor_snapshots_by_name=snapshots_by_factor,
            labels_by_session=labels_by_session,
            sessions=eval_sessions,
        )

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

        pit_facade = self._create_pit_facade(dataset_id)
        members = self._get_universe(dataset_id)
        universe = tuple(m.instrument_id for m in members)

        all_sessions = self._discover_sessions(dataset_id, universe, start_date, end_date)
        if not all_sessions:
            raise ValueError(f"Dataset '{dataset_id}' holds no market bars in the requested window")

        eval_sessions = self._rebalance_sessions(all_sessions)

        # Compute composite snapshots
        composite_snapshots: list[FactorSnapshot] = []
        for sess in eval_sessions:
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
            all_sessions=all_sessions,
            eval_sessions=eval_sessions,
        )

        evaluator = FactorEvaluator(spec or EvaluationSpec())
        return evaluator.evaluate(composite_snapshots, forward_returns)
