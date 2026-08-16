"""Tests for MCP research tools."""

from apps.mcp.tools import get_default_tools


def test_mcp_tools_list_and_execution() -> None:
    tools = {t.name: t for t in get_default_tools()}

    assert "list_datasets" in tools
    assert "run_factor_backtest" in tools
    assert "evaluate_validation_gates" in tools

    backtest_res = tools["run_factor_backtest"].handler({"factor_name": "momentum_12_1"})
    assert isinstance(backtest_res, dict)
    assert backtest_res["factor_name"] == "momentum_12_1"
    assert backtest_res["mean_ic"] > 0
