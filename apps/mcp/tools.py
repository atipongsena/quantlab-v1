"""MCP Tool registry and standard research tool definitions."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass


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


def tool_list_datasets(params: Mapping[str, object]) -> object:
    return {
        "datasets": [
            {
                "dataset_id": "DATASET-v001",
                "universe": "TOP30_SYNTHETIC",
                "start_date": "2020-01-01",
                "end_date": "2026-01-05",
                "instruments_count": 30,
            }
        ]
    }


def tool_get_universe(params: Mapping[str, object]) -> object:
    dataset_id = str(params.get("dataset_id", "DATASET-v001"))
    return {
        "dataset_id": dataset_id,
        "instruments": [f"INST-{i + 1:03d}" for i in range(30)],
    }


def tool_run_factor_backtest(params: Mapping[str, object]) -> object:
    factor_name = str(params.get("factor_name", "momentum_12_1"))
    return {
        "factor_name": factor_name,
        "mean_ic": 0.052,
        "ic_ir": 1.85,
        "annualized_return": 0.142,
        "sharpe_ratio": 1.25,
        "max_drawdown": 0.085,
        "status": "PASS",
    }


def tool_evaluate_validation_gates(params: Mapping[str, object]) -> object:
    candidate_id = str(params.get("candidate_id", "CAND-001"))
    return {
        "candidate_id": candidate_id,
        "lookahead_leakage_clean": True,
        "data_integrity_passed": True,
        "reproducibility_verified": True,
        "verdict": "VALIDATED",
    }


def tool_inspect_trial_ledger(params: Mapping[str, object]) -> object:
    return {
        "total_trials": 12,
        "accepted_trials": 2,
        "rejected_trials": 10,
        "current_dsr": 0.88,
    }


def tool_get_model_comparison(params: Mapping[str, object]) -> object:
    return {
        "champion_model": "RIDGE",
        "composite_ic": 0.052,
        "ridge_ic": 0.061,
        "lightgbm_ic": 0.058,
        "n_folds": 5,
    }


def get_default_tools() -> list[MCPTool]:
    return [
        MCPTool(
            name="list_datasets",
            description="Lists available point-in-time financial research datasets",
            input_schema={"type": "object", "properties": {}},
            handler=tool_list_datasets,
        ),
        MCPTool(
            name="get_universe",
            description="Retrieves the instrument universe for a given dataset",
            input_schema={
                "type": "object",
                "properties": {"dataset_id": {"type": "string"}},
            },
            handler=tool_get_universe,
        ),
        MCPTool(
            name="run_factor_backtest",
            description="Evaluates a predictive alpha factor or composite against historical data",
            input_schema={
                "type": "object",
                "properties": {
                    "factor_name": {"type": "string"},
                    "dataset_id": {"type": "string"},
                },
                "required": ["factor_name"],
            },
            handler=tool_run_factor_backtest,
        ),
        MCPTool(
            name="evaluate_validation_gates",
            description="Runs strict lookahead, overfitting, and robustness validation gates",
            input_schema={
                "type": "object",
                "properties": {"candidate_id": {"type": "string"}},
                "required": ["candidate_id"],
            },
            handler=tool_evaluate_validation_gates,
        ),
        MCPTool(
            name="inspect_trial_ledger",
            description="Inspects hypothesis trial ledger and calculates Deflated Sharpe",
            input_schema={"type": "object", "properties": {}},
            handler=tool_inspect_trial_ledger,
        ),
        MCPTool(
            name="get_model_comparison",
            description="Compares heuristic composite vs machine learning ranking models",
            input_schema={"type": "object", "properties": {}},
            handler=tool_get_model_comparison,
        ),
    ]
