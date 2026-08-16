"""Tests for MCP JSON-RPC transport and server execution."""

import json

from apps.mcp.server import MCPServer


def test_mcp_server_tools_list_rpc() -> None:
    server = MCPServer()
    req = {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "params": {},
        "id": "1",
    }
    resp_str = server.handle_request(req)
    resp = json.loads(resp_str)

    assert resp["jsonrpc"] == "2.0"
    assert resp["id"] == "1"
    assert "tools" in resp["result"]
    assert len(resp["result"]["tools"]) >= 6


def test_mcp_server_tool_call_rpc() -> None:
    server = MCPServer()
    req = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "run_factor_backtest",
            "arguments": {"factor_name": "quality_roe"},
        },
        "id": "2",
    }
    resp_str = server.handle_request(req)
    resp = json.loads(resp_str)

    assert resp["jsonrpc"] == "2.0"
    assert resp["id"] == "2"
    content = resp["result"]["content"]
    assert len(content) == 1
    tool_output = json.loads(content[0]["text"])
    assert tool_output["factor_name"] == "quality_roe"
