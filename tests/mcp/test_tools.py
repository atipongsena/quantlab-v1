"""Tests for MCP research tools."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from apps.mcp import tools as mcp_tools


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("QUANTLAB_HOME", str(tmp_path))
    return tmp_path


def _tools() -> dict[str, mcp_tools.MCPTool]:
    return {tool.name: tool for tool in mcp_tools.get_default_tools()}


def test_every_tool_declares_a_schema_and_handler() -> None:
    registry = _tools()
    assert registry
    for tool in registry.values():
        assert tool.description
        assert tool.input_schema["type"] == "object"
        assert callable(tool.handler)


def test_missing_artifact_returns_the_command_that_produces_it(workspace: Path) -> None:
    """An agent must be able to tell "not produced yet" from a real measurement.

    Returning a plausible-looking number here would be worse than failing: the agent has
    no way to know it is reasoning over a placeholder.
    """
    result = _tools()["get_backtest"].handler({})
    assert isinstance(result, dict)
    assert result["available"] is False
    assert "quantlab backtest run" in str(result["produce_with"])


def test_recorded_artifact_is_returned_with_provenance(workspace: Path) -> None:
    target = workspace / "artifacts" / "latest" / "validation-report.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"verdict": "RESEARCH_ONLY"}), encoding="utf-8")

    result = _tools()["get_validation"].handler({})
    assert isinstance(result, dict)
    assert result["verdict"] == "RESEARCH_ONLY"
    assert result["_artifact"]["path"].endswith("validation-report.json")


def test_backtest_tool_drops_the_full_equity_series(workspace: Path) -> None:
    """A ten-year equity curve is thousands of rows an agent does not need in context."""
    target = workspace / "artifacts" / "latest" / "backtest" / "manifest.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps({"strategy_id": "demo", "equity": {"2020-01-02": "1000000"}}),
        encoding="utf-8",
    )

    result = _tools()["get_backtest"].handler({})
    assert isinstance(result, dict)
    assert result["strategy_id"] == "demo"
    assert "equity" not in result


def test_list_datasets_says_so_when_nothing_is_built(workspace: Path) -> None:
    result = _tools()["list_datasets"].handler({})
    assert isinstance(result, dict)
    assert result["datasets"] == []
    assert "quantlab dataset build" in str(result["note"])
