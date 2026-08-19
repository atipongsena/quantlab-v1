"""End-to-end CLI tests for backtesting commands."""

from __future__ import annotations

import json
from pathlib import Path

from apps.cli.main import app

STRATEGY = "configs/strategies/synthetic-golden-v1.yaml"


def test_backtest_run_cli_json(in_synthetic_workspace: Path, capsys) -> None:
    code = app(
        [
            "backtest",
            "run",
            STRATEGY,
            "--dataset",
            "DATASET-v001",
            "--start",
            "2021-01-04",
            "--end",
            "2022-12-30",
            "--output",
            "json",
        ]
    )
    assert code == 0
    res = json.loads(capsys.readouterr().out)
    assert res["strategy_id"] == "synthetic-golden-v1"
    assert "metrics" in res
    assert "content_hash" in res


def test_backtest_run_cli_text(in_synthetic_workspace: Path, capsys) -> None:
    code = app(
        [
            "backtest",
            "run",
            STRATEGY,
            "--dataset",
            "DATASET-v001",
            "--start",
            "2021-01-04",
            "--end",
            "2022-12-30",
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "Backtest Execution Report: synthetic-golden-v1" in out
    assert "Sharpe Ratio" in out
    # The synthetic fixture carries an SPY series, so the benchmark block must appear.
    assert "Versus SPY" in out
