"""The walk-forward comparison must be reproducible run to run.

Determinism is the claim that makes a recorded result mean anything: if the same inputs
can produce a different rank IC, then no reported number can be checked, and a change
that shifts the result is indistinguishable from noise in the harness.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quantlab.application.models import ModelService

WALK_FORWARD = "configs/ml/determinism-test.yaml"


@pytest.fixture
def workspace(synthetic_workspace: Path) -> Path:
    path = synthetic_workspace / WALK_FORWARD
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "walk_forward_id: determinism-test",
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
    return synthetic_workspace


def _run(workspace: Path):
    # A fresh service each time, so the panel is rebuilt from disk rather than served
    # from the in-process cache. Caching the panel would hide an unstable build.
    return ModelService(base_dir=workspace).compare_models(
        dataset_id="DATASET-v001",
        walk_forward_config_path=WALK_FORWARD,
        output_path=workspace / "artifacts" / "mc.json",
    )


def test_comparison_is_reproducible_across_fresh_builds(workspace: Path) -> None:
    first = _run(workspace)
    second = _run(workspace)

    assert first.content_hash == second.content_hash
    assert [(r.model_name, r.mean_ic) for r in first.reports] == [
        (r.model_name, r.mean_ic) for r in second.reports
    ]


def test_panel_row_count_is_stable(workspace: Path) -> None:
    """An unstable panel size means session discovery is order-dependent."""
    service = ModelService(base_dir=workspace)
    first = service._panel("DATASET-v001", None, None, 21)
    second = ModelService(base_dir=workspace)._panel("DATASET-v001", None, None, 21)

    assert len(first.rows) == len(second.rows)
    assert first.sessions == second.sessions
    assert first.feature_names == second.feature_names


def test_label_shuffle_control_is_reproducible_for_a_fixed_seed(workspace: Path) -> None:
    a = ModelService(base_dir=workspace).run_label_shuffle_control(
        dataset_id="DATASET-v001", walk_forward_config_path=WALK_FORWARD, permutations=2, seed=7
    )
    b = ModelService(base_dir=workspace).run_label_shuffle_control(
        dataset_id="DATASET-v001", walk_forward_config_path=WALK_FORWARD, permutations=2, seed=7
    )

    assert [v.p_value for v in a.verdicts] == [v.p_value for v in b.verdicts]
    assert [v.null_mean for v in a.verdicts] == [v.null_mean for v in b.verdicts]
