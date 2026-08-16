"""Application service for strategy validation and falsification workflows."""

from __future__ import annotations

import json
import math
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from quantlab.application.backtests import BacktestService
from quantlab.validation.candidate import CandidateFreezer
from quantlab.validation.result import ValidationResult
from quantlab.validation.runner import ValidationRunner


class ValidationService:
    """Application service coordinating candidate freeze, validation, and artifacts."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self._base_dir = base_dir or Path.cwd()
        self._backtest_service = BacktestService(self._base_dir)

    def run_validation(
        self,
        config_path: str | Path = "configs/validation/default-v1.yaml",
        experiment_id: str = "EXP-SYNTHETIC",
        strategy_config_path: str | Path = "configs/strategies/composite-top30-v1.yaml",
        dataset_id: str = "DATASET-v001",
        output_path: Path | None = None,
    ) -> ValidationResult:
        # 1. Freeze candidate
        strat_cfg_path = Path(strategy_config_path)
        if not strat_cfg_path.is_absolute():
            strat_cfg_path = self._base_dir / strat_cfg_path
        strat_cfg: dict[str, object] = {}
        if strat_cfg_path.exists():
            with open(strat_cfg_path, encoding="utf-8") as f:
                strat_cfg = yaml.safe_load(f) or {}

        candidate = CandidateFreezer.freeze(
            strategy_id=str(strat_cfg.get("strategy_id", "composite-top30-v1")),
            strategy_config=strat_cfg,
            code_fingerprint=f"exp:{experiment_id}",
        )

        # 2. Run simulation or generate benchmark return series (252 sessions)
        returns_series = [0.0006 + 0.008 * math.sin(i * 0.15) for i in range(252)]

        # 3. Execute validation pipeline
        result = ValidationRunner.run(
            candidate=candidate,
            returns_series=returns_series,
        )

        # 4. Save validation artifact
        out_file = output_path or self._base_dir / "artifacts" / "latest" / "validation-report.json"
        out_file.parent.mkdir(parents=True, exist_ok=True)

        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(result.as_dict(), f, indent=2)

        return result
