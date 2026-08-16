"""CLI command handlers for ML model comparison and walk-forward evaluation."""

from __future__ import annotations

import argparse
import json

from quantlab.application.models import ModelService


def run_model_compare(args: argparse.Namespace) -> int:
    service = ModelService()

    result = service.compare_models(
        dataset_id=getattr(args, "dataset", "DATASET-v001"),
        walk_forward_config_path=getattr(args, "walk_forward", "configs/ml/walk-forward-v1.yaml"),
        model_names=getattr(args, "models", "composite,ridge,lightgbm"),
    )

    if getattr(args, "output", "text") == "json":
        print(json.dumps(result.as_dict(), indent=2))
        return 0

    print("=" * 70)
    print("QuantLab Walk-Forward Cross-Validation Model Comparison")
    print(f"Evaluated across {result.n_folds} purged folds")
    print("=" * 70)

    for rep in result.reports:
        print(f"Model: {rep.model_name.upper()}")
        print(f"  Mean Out-of-Sample Rank IC : {rep.mean_ic:.4f}")
        print(f"  IC Information Ratio (IR)  : {rep.ic_ir:.2f}")
        print(f"  Top/Bottom Quintile Spread : {rep.top_bottom_spread:.4f}")
        print(f"  Quintile Monotonicity      : {'YES' if rep.is_monotonic else 'NO'}")
        print("-" * 70)

    print(f"Champion Model : {result.champion_model.upper()}")
    print(f"Reason         : {result.champion_reason}")
    print("=" * 70)
    print("Status: PASS [Model comparison completed]")
    return 0
