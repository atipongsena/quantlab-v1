"""Model Context Protocol (MCP) Server implementation."""

from __future__ import annotations

import json
from collections.abc import Mapping

from .tools import MCPTool, get_default_tools
from .transport import JSONRPCRequest, JSONRPCResponse


class MCPServer:
    """Server hosting Model Context Protocol endpoints for autonomous agents."""

    def __init__(self, tools: list[MCPTool] | None = None) -> None:
        self._tools: dict[str, MCPTool] = {
            t.name: t for t in (tools if tools is not None else get_default_tools())
        }

    def handle_request(self, request_payload: Mapping[str, object] | str) -> str:
        if isinstance(request_payload, str):
            try:
                data = json.loads(request_payload)
            except json.JSONDecodeError:
                return JSONRPCResponse(
                    id=None,
                    error={"code": -32700, "message": "Parse error"},
                ).to_json()
        else:
            data = request_payload

        try:
            req = JSONRPCRequest.from_dict(data)
        except Exception as e:
            raw_err_id = data.get("id") if isinstance(data, dict) else None
            err_id: str | int | None = (
                str(raw_err_id) if isinstance(raw_err_id, (str, int)) else None
            )
            return JSONRPCResponse(
                id=err_id,
                error={"code": -32600, "message": f"Invalid Request: {e}"},
            ).to_json()

        if req.method == "tools/list":
            tools_list = [t.as_dict() for t in self._tools.values()]
            return JSONRPCResponse(id=req.id, result={"tools": tools_list}).to_json()

        if req.method == "tools/call":
            tool_name = str(req.params.get("name", ""))
            arguments = req.params.get("arguments", {})
            args_dict = dict(arguments) if isinstance(arguments, dict) else {}

            if tool_name not in self._tools:
                return JSONRPCResponse(
                    id=req.id,
                    error={"code": -32601, "message": f"Tool '{tool_name}' not found"},
                ).to_json()

            tool = self._tools[tool_name]
            try:
                result = tool.handler(args_dict)
                return JSONRPCResponse(
                    id=req.id,
                    result={"content": [{"type": "text", "text": json.dumps(result)}]},
                ).to_json()
            except Exception as ex:
                return JSONRPCResponse(
                    id=req.id,
                    error={"code": -32000, "message": f"Tool execution failed: {ex}"},
                ).to_json()

        return JSONRPCResponse(
            id=req.id,
            error={"code": -32601, "message": f"Method '{req.method}' not supported"},
        ).to_json()
