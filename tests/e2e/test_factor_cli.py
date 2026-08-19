"""End-to-end integration tests for factor CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

from apps.cli.main import app


def test_factor_list_cli_text() -> None:
    assert app(["factor", "list"]) == 0


def test_factor_list_cli_json(capsys) -> None:
    assert app(["factor", "list", "--output", "json"]) == 0
    factors = json.loads(capsys.readouterr().out)
    assert isinstance(factors, list)
    assert len(factors) >= 14
    # Every registered factor has to declare the direction and lookback the evaluator
    # relies on; a factor missing those silently scores as if higher were always better.
    for factor in factors:
        assert factor["direction"] in (-1, 1)
        assert factor["lookback_sessions"] > 0


def test_factor_research_cli_json(in_synthetic_workspace: Path, capsys) -> None:
    code = app(
        [
            "factor",
            "research",
            "momentum_12_1",
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
    assert res["factor_id"] == "momentum_12_1"
    assert res["diagnostic_label"] == "DIAGNOSTIC_ONLY_NON_DEPLOYABLE"
    assert res["num_sessions"] > 0
    assert set(res["decay_profile"]) == {"1M", "3M", "6M", "12M"}
    assert -1.0 <= res["rank_ic_mean"] <= 1.0


def test_factor_composite_cli_json(in_synthetic_workspace: Path, capsys) -> None:
    code = app(
        [
            "factor",
            "composite",
            "composite-v1",
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
    assert res["factor_id"] == "composite-v1"
    assert res["num_sessions"] > 0
