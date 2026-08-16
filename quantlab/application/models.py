"""Application service for model comparison and walk-forward workflows."""

from __future__ import annotations

import json
import math
import uuid
from datetime import date
from pathlib import Path

from quantlab.domain.identity import InstrumentId
from quantlab.ml.contracts import MLDataset, MLFeatureRow
from quantlab.ml.runner import ModelComparisonResult, ModelComparisonRunner
from quantlab.ml.splits import WalkForwardSpec, WindowType
from quantlab.ml.walk_forward import PurgedWalkForwardCV


class ModelService:
    """Coordinates walk-forward dataset generation, model comparison, and artifact saving."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self._base_dir = base_dir or Path.cwd()

    def compare_models(
        self,
        dataset_id: str = "DATASET-v001",
        walk_forward_config_path: str | Path = "configs/ml/walk-forward-v1.yaml",
        model_names: str = "composite,ridge,lightgbm",
        output_path: Path | None = None,
    ) -> ModelComparisonResult:
        # 1. Generate 500 sessions of 30-instrument synthetic cross-sectional dataset
        insts = [InstrumentId(uuid.UUID(int=i + 1)) for i in range(30)]
        start_date = date(2022, 1, 3)
        sessions = [date.fromordinal(start_date.toordinal() + i) for i in range(500)]

        rows: list[MLFeatureRow] = []
        for s_idx, s in enumerate(sessions):
            for i_idx, inst in enumerate(insts):
                # 3 features: momentum, value, quality
                f1 = math.sin(s_idx * 0.05 + i_idx * 0.3)  # momentum
                f2 = math.cos(s_idx * 0.03 + i_idx * 0.5)  # value
                f3 = (i_idx % 5) * 0.2 - 0.5  # quality
                # Ground truth target with subtle linear + non-linear relation
                true_label = 0.02 * f1 + 0.01 * f2 + 0.015 * f3 + 0.005 * (f1 * f2)
                rows.append(
                    MLFeatureRow(
                        session=s,
                        instrument_id=inst,
                        features=(f1, f2, f3),
                        label=true_label,
                    )
                )

        dataset = MLDataset(
            dataset_id=dataset_id,
            feature_names=("momentum_12_1", "value_composite", "quality_roe"),
            rows=tuple(rows),
        )

        # 2. Split walk-forward folds
        spec = WalkForwardSpec(
            window_type=WindowType.EXPANDING,
            min_train_sessions=200,
            test_window_sessions=50,
            step_sessions=50,
            purge_sessions=21,
            embargo_sessions=5,
        )
        folds = PurgedWalkForwardCV.split(sessions, spec)

        # 3. Run comparison
        result = ModelComparisonRunner.run_comparison(dataset, folds)

        # 4. Save artifact
        out_file = output_path or self._base_dir / "artifacts" / "latest" / "model-comparison.json"
        out_file.parent.mkdir(parents=True, exist_ok=True)

        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(result.as_dict(), f, indent=2)

        return result
