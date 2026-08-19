"""End-to-end CLI tests for quantlab model compare."""

from __future__ import annotations

import json
from pathlib import Path

from apps.cli.main import app

# The synthetic fixture spans 2020-2023, so a 12-month training minimum with 6-month
# test blocks is the largest walk-forward it can support.
WALK_FORWARD = "configs/ml/walk-forward-synthetic.yaml"


def _write_walk_forward(workspace: Path) -> None:
    path = workspace / WALK_FORWARD
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "walk_forward_id: walk-forward-synthetic",
                "split:",
                "  window_type: expanding",
                "  min_train_sessions: 12",
                "  test_window_sessions: 6",
                "  step_sessions: 6",
                "  purge_sessions: 1",
                "  embargo_sessions: 1",
            ]
        ),
        encoding="utf-8",
    )


def test_model_compare_cli_json(in_synthetic_workspace: Path, capsys) -> None:
    _write_walk_forward(in_synthetic_workspace)
    code = app(
        [
            "model",
            "compare",
            "--dataset",
            "DATASET-v001",
            "--walk-forward",
            WALK_FORWARD,
            "--output",
            "json",
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert "champion_model" in payload
    assert payload["reports"], "comparison produced no model reports"


def test_model_compare_cli_text(in_synthetic_workspace: Path, capsys) -> None:
    _write_walk_forward(in_synthetic_workspace)
    code = app(
        [
            "model",
            "compare",
            "--dataset",
            "DATASET-v001",
            "--walk-forward",
            WALK_FORWARD,
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "Purged walk-forward model comparison" in out
    assert "Champion" in out


def test_label_shuffle_control_reports_a_permutation_p_value(
    in_synthetic_workspace: Path,
) -> None:
    """The control must return a distribution, not a single shuffled score.

    Models are refit per fold, so one shuffle landing above the real score is ordinary
    sampling noise. Comparing against several permutations is what makes the control a
    test rather than a coin flip (spec 4.16).
    """
    from quantlab.application.models import ModelService

    _write_walk_forward(in_synthetic_workspace)
    service = ModelService(base_dir=in_synthetic_workspace)
    control = service.run_label_shuffle_control(
        dataset_id="DATASET-v001",
        walk_forward_config_path=WALK_FORWARD,
        permutations=3,
    )

    assert len(control.permuted) == 3
    assert control.verdicts, "control produced no per-model verdicts"
    for verdict in control.verdicts:
        assert verdict.permutations == 3
        # Add-one smoothing bounds the attainable p-value away from an unqualified zero.
        assert 1 / 4 <= verdict.p_value <= 1.0
