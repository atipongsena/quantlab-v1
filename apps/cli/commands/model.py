"""CLI command handlers for ML model comparison and walk-forward evaluation."""

from __future__ import annotations

import argparse
import json
from datetime import date

from quantlab.application.models import ModelService


def _print_reports(title: str, result: object) -> None:
    print(f"{title}")
    print("-" * 70)
    for rep in result.reports:  # type: ignore[attr-defined]
        print(
            f"  {rep.model_name:<10} rank IC {rep.mean_ic:+.4f}  "
            f"IR {rep.ic_ir:+.2f}  Q5-Q1 {rep.top_bottom_spread:+.4f}  "
            f"monotonic {'yes' if rep.is_monotonic else 'no'}"
        )


def run_model_compare(args: argparse.Namespace) -> int:
    # One service instance, so the comparison and its control share the built panel.
    service = ModelService()
    start = date.fromisoformat(args.start) if getattr(args, "start", None) else None
    end = date.fromisoformat(args.end) if getattr(args, "end", None) else None

    result = service.compare_models(
        dataset_id=getattr(args, "dataset", "DATASET-US-30Y-v001"),
        walk_forward_config_path=getattr(args, "walk_forward", "configs/ml/walk-forward-v1.yaml"),
        model_names=getattr(args, "models", "composite,ridge,gbdt"),
        start_date=start,
        end_date=end,
    )

    if getattr(args, "output", "text") == "json":
        print(json.dumps(result.as_dict(), indent=2))
        return 0

    print("=" * 70)
    print("Purged walk-forward model comparison")
    print(f"{result.n_folds} folds, monthly cross-sections, labels purged and embargoed")
    print("=" * 70)
    _print_reports("Out-of-sample results", result)

    if getattr(args, "control", False):
        permutations = int(getattr(args, "permutations", 5))
        control = service.run_label_shuffle_control(
            dataset_id=getattr(args, "dataset", "DATASET-US-30Y-v001"),
            walk_forward_config_path=getattr(
                args, "walk_forward", "configs/ml/walk-forward-v1.yaml"
            ),
            permutations=permutations,
            start_date=start,
            end_date=end,
        )
        print("=" * 70)
        print(f"Label-shuffle permutation test ({permutations} permutations)")
        print("Labels shuffled within each cross-section; features and folds unchanged.")
        print("-" * 70)
        for verdict in control.verdicts:
            marker = "survives" if verdict.survives else "INDISTINGUISHABLE"
            print(
                f"  {verdict.model_name:<10} real {verdict.observed_rank_ic:+.4f}  "
                f"shuffled mean {verdict.null_mean:+.4f} max {verdict.null_max:+.4f}  "
                f"p={verdict.p_value:.3f}  {marker}"
            )
        print("-" * 70)
        weak = [v.model_name for v in control.verdicts if not v.survives]
        if weak:
            print(f"  {', '.join(weak)} scored no better than shuffled labels.")
            print("  Expected for a signal this weak, and not evidence of leakage, but")
            print("  the measured skill cannot be distinguished from noise.")
        else:
            print("  Every real score sits outside the shuffled-label distribution.")

    print("=" * 70)
    print(f"Champion : {result.champion_model}")
    print(f"Reason   : {result.champion_reason}")
    print("=" * 70)
    return 0
