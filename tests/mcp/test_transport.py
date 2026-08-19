"""Tests for MCP JSON-RPC transport and server execution."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from apps.mcp.server import MCPServer


def test_mcp_server_tools_list_rpc() -> None:
    server = MCPServer()
    req = {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "params": {},
        "id": "1",
    }
    resp = json.loads(server.handle_request(req))

    assert resp["jsonrpc"] == "2.0"
    assert resp["id"] == "1"
    names = {tool["name"] for tool in resp["result"]["tools"]}
    assert {"list_evidence", "get_backtest", "get_validation"} <= names


def test_mcp_server_tool_call_rpc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QUANTLAB_HOME", str(tmp_path))
    server = MCPServer()
    req = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "list_evidence", "arguments": {}},
        "id": "2",
    }
    resp = json.loads(server.handle_request(req))

    assert resp["jsonrpc"] == "2.0"
    assert resp["id"] == "2"
    content = resp["result"]["content"]
    assert len(content) == 1

    payload = json.loads(content[0]["text"])
    assert payload["artifacts"], "the inventory should list what could be produced"
    assert all(row["produced_by"] for row in payload["artifacts"])


def test_unknown_method_returns_a_json_rpc_error() -> None:
    resp = json.loads(
        MCPServer().handle_request(
            {"jsonrpc": "2.0", "method": "tools/nope", "params": {}, "id": "3"}
        )
    )
    assert "error" in resp
    assert resp["id"] == "3"


def test_malformed_payload_returns_a_parse_error() -> None:
    resp = json.loads(MCPServer().handle_request("{not json"))
    assert resp["error"]["code"] == -32700
