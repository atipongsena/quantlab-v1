"""MCP tool registry over QuantLab's recorded evidence.

Every tool reads an artifact the CLI produced. None of them start a run: a thirty-year
backtest takes minutes and a tool call that silently returned a plausible number instead
would be worse than one that fails.

When an artifact does not exist yet the tool says so and names the command that produces
it, so an agent can act on the gap rather than reason over a placeholder.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from apps.api.artifacts import ArtifactNotFound, ArtifactStore
from quantlab.data.datasets import DatasetUniverseResolver
from quantlab.infrastructure.analytical_store import LocalAnalyticalStore


@dataclass(frozen=True, slots=True)
class MCPTool:
    name: str
    description: str
    input_schema: Mapping[str, object]
    handler: Callable[[Mapping[str, object]], object]

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": dict(self.input_schema),
        }


def _base_dir() -> Path:
    return Path(os.environ.get("QUANTLAB_HOME", Path.cwd()))


def _store() -> ArtifactStore:
    return ArtifactStore(_base_dir())


def _read(key: str) -> dict[str, Any]:
    try:
        return _store().load(key)
    except ArtifactNotFound as err:
        return {
            "available": False,
            "error": str(err),
            "produce_with": err.command,
        }


def tool_list_datasets(params: Mapping[str, object]) -> object:
    """Datasets that have actually been built into this working directory."""
    base = _base_dir()
    resolver = DatasetUniverseResolver(LocalAnalyticalStore(base / "data"))
    datasets: list[dict[str, object]] = []

    data_dir = base / "data"
    if data_dir.is_dir():
        for candidate in sorted(data_dir.iterdir()):
            if not candidate.is_dir() or not (candidate / "instruments").is_dir():
                continue
            try:
                members = resolver.members(candidate.name)
            except Exception:  # noqa: BLE001 - an unreadable roster is skipped, not fatal
                continue
            equities = [m for m in members if not m.is_etf]
            datasets.append(
                {
                    "dataset_id": candidate.name,
                    "instruments_count": len(members),
                    "equities_count": len(equities),
                    "etfs_count": len(members) - len(equities),
                    "sectors": sorted({m.sector for m in equities}),
                }
            )

    if not datasets:
        return {
            "datasets": [],
            "note": "No dataset has been built here. Run: quantlab dataset build <config>",
        }
    return {"datasets": datasets}


def tool_get_universe(params: Mapping[str, object]) -> object:
    """The equity cross-section a dataset publishes, ETFs excluded."""
    dataset_id = str(params.get("dataset_id", "DATASET-US-30Y-v001"))
    resolver = DatasetUniverseResolver(LocalAnalyticalStore(_base_dir() / "data"))
    try:
        members = resolver.equities(dataset_id)
    except Exception as err:  # noqa: BLE001 - reported to the agent as data, not a crash
        return {"dataset_id": dataset_id, "available": False, "error": str(err)}

    return {
        "dataset_id": dataset_id,
        "count": len(members),
        "instruments": [
            {"symbol": m.symbol, "sector": m.sector, "exchange": m.exchange} for m in members
        ],
    }


def tool_get_factor_research(params: Mapping[str, object]) -> object:
    """The most recent single-factor research report."""
    return _read("factor-research")


def tool_get_backtest(params: Mapping[str, object]) -> object:
    """The most recent backtest, without the full equity series."""
    payload = _read("backtest")
    payload.pop("equity", None)
    return payload


def tool_get_validation(params: Mapping[str, object]) -> object:
    """The most recent falsification report, including the lifecycle verdict."""
    return _read("validation")


def tool_get_model_comparison(params: Mapping[str, object]) -> object:
    """The most recent purged walk-forward comparison."""
    return _read("model-comparison")


def tool_get_market_data_verification(params: Mapping[str, object]) -> object:
    """Corporate-action adjustment checked against the provider's own series."""
    payload = _read("market-data-verification")
    payload.pop("per_instrument", None)
    return payload


def tool_list_evidence(params: Mapping[str, object]) -> object:
    """Every artifact this server can read, and the command that produces each one."""
    return {"artifacts": _store().inventory()}


def get_default_tools() -> list[MCPTool]:
    no_params: Mapping[str, object] = {"type": "object", "properties": {}}
    dataset_param: Mapping[str, object] = {
        "type": "object",
        "properties": {"dataset_id": {"type": "string"}},
    }

    return [
        MCPTool(
            name="list_evidence",
            description=(
                "Lists every research artifact available to read, whether it has been "
                "produced yet, and the command that produces it"
            ),
            input_schema=no_params,
            handler=tool_list_evidence,
        ),
        MCPTool(
            name="list_datasets",
            description="Lists point-in-time datasets built into this working directory",
            input_schema=no_params,
            handler=tool_list_datasets,
        ),
        MCPTool(
            name="get_universe",
            description="Returns a dataset's equity cross-section with sectors, ETFs excluded",
            input_schema=dataset_param,
            handler=tool_get_universe,
        ),
        MCPTool(
            name="get_factor_research",
            description=(
                "Returns the recorded factor research report: rank IC with Newey-West "
                "t-statistic, horizon decay, quantile portfolios, and IC stability by year"
            ),
            input_schema=no_params,
            handler=tool_get_factor_research,
        ),
        MCPTool(
            name="get_backtest",
            description=(
                "Returns the recorded backtest: performance metrics, costs, and the "
                "benchmark comparison with beta, alpha, and information ratio"
            ),
            input_schema=no_params,
            handler=tool_get_backtest,
        ),
        MCPTool(
            name="get_validation",
            description=(
                "Returns the recorded falsification report: hard gates, parameter sweep, "
                "factor ablations, bootstrap interval, deflated Sharpe, and the verdict"
            ),
            input_schema=no_params,
            handler=tool_get_validation,
        ),
        MCPTool(
            name="get_model_comparison",
            description="Returns the recorded purged walk-forward model comparison",
            input_schema=no_params,
            handler=tool_get_model_comparison,
        ),
        MCPTool(
            name="get_market_data_verification",
            description=(
                "Returns the corporate-action verification report: the engine's own "
                "adjustment replayed against the data provider's independent series"
            ),
            input_schema=no_params,
            handler=tool_get_market_data_verification,
        ),
    ]
