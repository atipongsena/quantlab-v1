"""JSON-RPC 2.0 request and response contracts for Model Context Protocol."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class JSONRPCRequest:
    method: str
    params: Mapping[str, object]
    id: str | int | None = None
    jsonrpc: str = "2.0"

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> JSONRPCRequest:
        if data.get("jsonrpc") != "2.0":
            raise ValueError("Invalid JSON-RPC version; must be '2.0'")
        method = str(data.get("method", ""))
        raw_params = data.get("params")
        params: dict[str, object] = dict(raw_params) if isinstance(raw_params, Mapping) else {}
        raw_id = data.get("id")
        req_id: str | int | None = str(raw_id) if isinstance(raw_id, (str, int)) else None
        return cls(method=method, params=params, id=req_id)


@dataclass(frozen=True, slots=True)
class JSONRPCResponse:
    id: str | int | None
    result: object | None = None
    error: Mapping[str, object] | None = None
    jsonrpc: str = "2.0"

    def as_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "jsonrpc": self.jsonrpc,
            "id": self.id,
        }
        if self.error is not None:
            payload["error"] = dict(self.error)
        else:
            payload["result"] = self.result
        return payload

    def to_json(self) -> str:
        return json.dumps(self.as_dict())
