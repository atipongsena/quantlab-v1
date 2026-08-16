"""End-to-end CLI tests for backtesting commands."""

import json

from apps.cli.main import app


def test_backtest_run_cli_json(capsys) -> None:
    code = app(
        [
            "backtest",
            "run",
            "configs/strategies/composite-top30-v1.yaml",
            "--dataset",
            "DATASET-v001",
            "--output",
            "json",
        ]
    )
    assert code == 0
    captured = capsys.readouterr()
    res = json.loads(captured.out)
    assert res["strategy_id"] == "composite-top30-v1"
    assert "metrics" in res
    assert "content_hash" in res


def test_backtest_run_cli_text() -> None:
    code = app(
        [
            "backtest",
            "run",
            "configs/strategies/composite-top30-v1.yaml",
            "--dataset",
            "DATASET-v001",
        ]
    )
    assert code == 0
