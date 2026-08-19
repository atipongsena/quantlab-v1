"""Application service for strategy validation and falsification workflows."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from quantlab.application.backtests import BacktestService, PreparedBacktest
from quantlab.backtest.result import BacktestResult
from quantlab.domain.identity import InstrumentId
from quantlab.validation.candidate import CandidateFreezer
from quantlab.validation.result import ValidationResult
from quantlab.validation.robustness import RobustnessRunner
from quantlab.validation.runner import ValidationRunner
from quantlab.validation.sensitivity import SensitivityCell

DEFAULT_TOP_K_GRID = (20, 30, 50)


class ValidationService:
    """Coordinates candidate freeze, real robustness re-runs, and validation artifacts."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self._base_dir = base_dir or Path.cwd()
        self._backtest_service = BacktestService(self._base_dir)

    @staticmethod
    def _annual_turnover(result: BacktestResult) -> float:
        """Turnover per year, from the total the engine accumulated over the run."""
        sessions = len(result.equity_series)
        if sessions < 2:
            return 0.0
        years = sessions / 252.0
        return float(result.metrics.total_turnover) / years if years > 0 else 0.0

    @staticmethod
    def _terminal_weights(result: BacktestResult) -> dict[InstrumentId, Decimal]:
        if not result.portfolio_snapshots:
            return {}
        last_session = max(result.portfolio_snapshots)
        snapshot = result.portfolio_snapshots[last_session]
        total = snapshot.cash + sum(p.market_value for p in snapshot.positions)
        if total <= 0:
            return {}
        return {p.instrument_id: (p.market_value / total) for p in snapshot.positions}

    @staticmethod
    def _sector_weights(
        weights: dict[InstrumentId, Decimal],
        sectors: dict[InstrumentId, str],
    ) -> dict[str, Decimal]:
        totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        for instrument, weight in weights.items():
            totals[sectors.get(instrument, "UNKNOWN")] += weight
        return dict(totals)

    @staticmethod
    def _subperiod_cagr(result: BacktestResult) -> dict[str, float]:
        """Annual return by calendar year.

        A single aggregate CAGR hides whether the whole result came from one year
        (spec 7.7). Splitting it out is the cheapest way to see that.
        """
        by_year: dict[int, float] = {}
        for session, ret in sorted(result.daily_returns.items()):
            by_year[session.year] = (1.0 + by_year.get(session.year, 0.0)) * (1.0 + ret) - 1.0
        return {str(year): value for year, value in sorted(by_year.items())}

    def _sensitivity_cells(
        self,
        prepared: PreparedBacktest,
        baseline: BacktestResult,
        top_k_grid: tuple[int, ...],
    ) -> list[SensitivityCell]:
        """Re-run the strategy at each portfolio size.

        A parameter surface is only evidence if each point is a real run. The prepared
        study shares its factor snapshots across variants, so the sweep costs one
        simulation pass per point rather than a full recomputation.
        """
        cells: list[SensitivityCell] = []
        baseline_k = prepared.spec.portfolio_spec.target_size
        for top_k in sorted({*top_k_grid, baseline_k}):
            result = baseline if top_k == baseline_k else prepared.run(target_size=top_k)
            cells.append(
                SensitivityCell(
                    parameters={"top_k": top_k},
                    sharpe_ratio=float(result.metrics.sharpe_ratio),
                    cagr=float(result.metrics.cagr),
                    max_drawdown=float(result.metrics.max_drawdown),
                )
            )
        return cells

    def _ablations(
        self,
        prepared: PreparedBacktest,
    ) -> dict[str, tuple[float, float]]:
        """Re-run with each factor sleeve removed and the rest renormalized."""
        results: dict[str, tuple[float, float]] = {}
        weights = prepared.composite_spec.factor_weights
        if len(weights) < 2:
            return results
        for factor_id in weights:
            ablated = prepared.run(drop_factors=[factor_id])
            results[factor_id] = (
                float(ablated.metrics.sharpe_ratio),
                float(ablated.metrics.cagr),
            )
        return results

    def run_validation(
        self,
        config_path: str | Path = "configs/validation/default-v1.yaml",
        experiment_id: str = "EXP-US-PRICE-COMPOSITE",
        strategy_config_path: str | Path = "configs/strategies/us-price-composite-v1.yaml",
        dataset_id: str = "DATASET-US-30Y-v001",
        start_date: date | None = None,
        end_date: date | None = None,
        run_sweeps: bool = True,
        output_path: Path | None = None,
    ) -> ValidationResult:
        """Falsify a candidate against its own realized returns.

        Everything downstream reads the strategy's actual daily return series and real
        re-runs of it. Validating a stand-in series would produce a verdict about the
        stand-in.
        """
        strat_cfg_path = Path(strategy_config_path)
        if not strat_cfg_path.is_absolute():
            strat_cfg_path = self._base_dir / strat_cfg_path
        strat_cfg: dict[str, object] = {}
        if strat_cfg_path.exists():
            with open(strat_cfg_path, encoding="utf-8") as f:
                strat_cfg = yaml.safe_load(f) or {}

        val_cfg_path = Path(config_path)
        if not val_cfg_path.is_absolute():
            val_cfg_path = self._base_dir / val_cfg_path
        val_cfg: dict[str, Any] = {}
        if val_cfg_path.exists():
            with open(val_cfg_path, encoding="utf-8") as f:
                val_cfg = yaml.safe_load(f) or {}
        robustness_cfg: dict[str, Any] = val_cfg.get("robustness") or {}
        top_k_grid: tuple[int, ...] = tuple(robustness_cfg.get("top_k_grid") or DEFAULT_TOP_K_GRID)

        candidate = CandidateFreezer.freeze(
            strategy_id=str(strat_cfg.get("strategy_id", "us-price-composite-v1")),
            strategy_config=strat_cfg,
            code_fingerprint=f"exp:{experiment_id}",
        )

        prepared = self._backtest_service.prepare(
            strategy_config_path=strategy_config_path,
            dataset_id=dataset_id,
            start_date=start_date,
            end_date=end_date,
        )
        baseline = prepared.run()
        returns_series = [baseline.daily_returns[s] for s in sorted(baseline.daily_returns)]

        if run_sweeps:
            top_k_cells = self._sensitivity_cells(prepared, baseline, top_k_grid)
            ablation_results = self._ablations(prepared)
        else:
            top_k_cells = [
                SensitivityCell(
                    parameters={"top_k": prepared.spec.portfolio_spec.target_size},
                    sharpe_ratio=float(baseline.metrics.sharpe_ratio),
                    cagr=float(baseline.metrics.cagr),
                    max_drawdown=float(baseline.metrics.max_drawdown),
                )
            ]
            ablation_results = {}

        weights = self._terminal_weights(baseline)
        sector_weights = self._sector_weights(weights, dict(prepared.sectors))

        # The realized CAGR already carries the base cost assumption, so add it back
        # before sweeping costs; otherwise the sweep charges the strategy twice at the
        # baseline point.
        annual_turnover = self._annual_turnover(baseline)
        base_cost_bps = float(prepared.spec.slippage_bps)
        gross_cagr = float(baseline.metrics.cagr) + annual_turnover * (base_cost_bps / 10000.0) * 2

        robustness = RobustnessRunner.run(
            candidate=candidate,
            top_k_cells=top_k_cells,
            zero_cost_cagr=gross_cagr,
            annual_turnover=annual_turnover,
            terminal_weights=weights,
            sector_weights=sector_weights,
            ablation_results=ablation_results,
            baseline_sharpe=float(baseline.metrics.sharpe_ratio),
            baseline_cagr=float(baseline.metrics.cagr),
            subperiod_cagr=self._subperiod_cagr(baseline),
        )

        # Trials that were actually run this session: the base configuration plus every
        # sweep point. Deflating against a larger imagined trial count would be as
        # dishonest as deflating against one.
        trial_sharpes = [cell.sharpe_ratio for cell in top_k_cells]
        trial_sharpes.extend(sharpe for sharpe, _ in ablation_results.values())

        result = ValidationRunner.run(
            candidate=candidate,
            returns_series=returns_series,
            trial_sharpes=trial_sharpes,
            robustness=robustness,
        )

        out_file = output_path or self._base_dir / "artifacts" / "latest" / "validation-report.json"
        out_file.parent.mkdir(parents=True, exist_ok=True)
        payload = result.as_dict()
        payload["run"] = {
            "dataset_id": dataset_id,
            "strategy_config": str(strategy_config_path),
            "start_session": prepared.spec.start_session.isoformat(),
            "end_session": prepared.spec.end_session.isoformat(),
            "sessions": len(returns_series),
            "annual_turnover": round(annual_turnover, 4),
            "baseline_cagr": round(float(baseline.metrics.cagr), 6),
            "gross_of_cost_cagr": round(gross_cagr, 6),
            "sweeps_run": run_sweeps,
        }
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        return result
