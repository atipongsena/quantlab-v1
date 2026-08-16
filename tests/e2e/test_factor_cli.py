"""End-to-end integration tests for factor CLI commands."""

import json

from apps.cli.main import app


def test_factor_list_cli_text() -> None:
    code = app(["factor", "list"])
    assert code == 0


def test_factor_list_cli_json(capsys) -> None:
    code = app(["factor", "list", "--output", "json"])
    assert code == 0
    captured = capsys.readouterr()
    factors = json.loads(captured.out)
    assert isinstance(factors, list)
    assert len(factors) >= 14


def test_factor_research_cli_json(capsys) -> None:
    code = app(
        ["factor", "research", "momentum_12_1", "--dataset", "DATASET-v001", "--output", "json"]
    )
    assert code == 0
    captured = capsys.readouterr()
    res = json.loads(captured.out)
    assert res["factor_id"] == "momentum_12_1"
    assert "ic_mean" in res
    assert "decay_profile" in res
    assert res["diagnostic_label"] == "DIAGNOSTIC_ONLY_NON_DEPLOYABLE"


def test_factor_composite_cli_json(capsys) -> None:
    code = app(
        ["factor", "composite", "composite-v1", "--dataset", "DATASET-v001", "--output", "json"]
    )
    assert code == 0
    captured = capsys.readouterr()
    res = json.loads(captured.out)
    assert res["factor_id"] == "composite-v1"
    assert "ic_mean" in res
