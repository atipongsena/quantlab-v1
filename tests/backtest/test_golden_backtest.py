"""Golden regression: the synthetic backtest must stay bit-for-bit reproducible.

The previous version of this test compared whatever happened to be sitting in
``artifacts/latest/backtest`` against a checked-in snapshot, and passed silently when
either directory was absent - so it reported green both when nothing had been run and
when the last run was for an unrelated dataset. This version builds the committed
synthetic fixture into a temporary workspace, runs a fixed strategy end to end, and
compares the result against a golden record, which is what makes a determinism claim
mean anything.

Regenerate the golden record deliberately, after reviewing why the numbers moved:

    python scripts/regenerate_golden.py
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from quantlab.application.backtests import BacktestService
from quantlab.application.dataset_service import DatasetService

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_PATH = REPO_ROOT / "artifacts" / "golden" / "synthetic_v1" / "backtest-golden.json"

DATASET_CONFIG = "configs/datasets/synthetic-v001.yaml"
STRATEGY_CONFIG = "configs/strategies/synthetic-golden-v1.yaml"
DATASET_ID = "DATASET-v001"
START = date(2021, 1, 4)
END = date(2022, 12, 30)


def _prepare_workspace(tmp_path: Path) -> Path:
    """Copy the inputs a run needs into an isolated workspace."""
    for relative in (
        "configs",
        "migrations",
        "data/fixtures/synthetic_v1",
    ):
        source = REPO_ROOT / relative
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            import shutil

            shutil.copytree(source, target)
    return tmp_path


def _run(workspace: Path):
    DatasetService(base_dir=workspace).build_dataset(DATASET_CONFIG)
    service = BacktestService(base_dir=workspace)
    return service.run_backtest(
        strategy_config_path=STRATEGY_CONFIG,
        dataset_id=DATASET_ID,
        start_date=START,
        end_date=END,
        output_dir=workspace / "artifacts" / "run",
    )


def _summary(result) -> dict[str, object]:
    metrics = result.metrics
    return {
        "strategy_id": result.spec.strategy_id,
        "start_session": result.spec.start_session.isoformat(),
        "end_session": result.spec.end_session.isoformat(),
        "sessions": len(result.equity_series),
        "orders": len(result.orders),
        "fills": len(result.fills),
        "total_return": round(metrics.total_return, 10),
        "cagr": round(metrics.cagr, 10),
        "sharpe_ratio": round(metrics.sharpe_ratio, 10),
        "max_drawdown": round(metrics.max_drawdown, 10),
        "total_turnover": round(metrics.total_turnover, 10),
        "content_hash": result.content_hash,
    }


@pytest.fixture(scope="module")
def golden_run(tmp_path_factory: pytest.TempPathFactory) -> dict[str, object]:
    workspace = _prepare_workspace(tmp_path_factory.mktemp("golden"))
    return _summary(_run(workspace))


def test_golden_backtest_matches_recorded_run(golden_run: dict[str, object]) -> None:
    if not GOLDEN_PATH.exists():
        pytest.skip(f"No golden record at {GOLDEN_PATH}; run scripts/regenerate_golden.py")

    expected = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    assert golden_run == expected, (
        "Backtest output drifted from the golden record. If the change is intended, "
        "review the diff and regenerate with scripts/regenerate_golden.py."
    )


def test_backtest_is_deterministic_across_runs(tmp_path_factory: pytest.TempPathFactory) -> None:
    """Same inputs, same seed, separate workspaces: the content hash must match."""
    first = _summary(_run(_prepare_workspace(tmp_path_factory.mktemp("determinism_a"))))
    second = _summary(_run(_prepare_workspace(tmp_path_factory.mktemp("determinism_b"))))
    assert first["content_hash"] == second["content_hash"]
    assert first == second
