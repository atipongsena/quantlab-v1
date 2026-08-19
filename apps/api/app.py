"""REST API serving QuantLab evidence artifacts.

Run it with:

    python -m uvicorn apps.api.app:app --port 8000

Interactive schema at http://localhost:8000/docs.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from apps.api.artifacts import ArtifactNotFound, ArtifactStore
from quantlab.data.datasets import DatasetUniverseResolver
from quantlab.infrastructure.analytical_store import LocalAnalyticalStore

BASE_DIR = Path(os.environ.get("QUANTLAB_HOME", Path.cwd()))

app = FastAPI(
    title="QuantLab API",
    version="1.0.0",
    description=(
        "Serves the evidence artifacts produced by the QuantLab CLI: factor research, "
        "backtests, validation verdicts, walk-forward model comparisons, and the "
        "corporate-action verification report. Runs are started from the CLI, not from "
        "here, so every number served is traceable to a hashed artifact on disk."
    ),
)

# The dashboard is served from a separate origin in development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_methods=["GET"],
    allow_headers=["*"],
)

store = ArtifactStore(BASE_DIR)


@app.get("/health", tags=["system"])
def health() -> dict[str, Any]:
    """Liveness plus which evidence is currently on disk."""
    inventory = store.inventory()
    return {
        "status": "ok",
        "version": app.version,
        "base_dir": str(store.base_dir),
        "artifacts_available": sum(1 for row in inventory if row["available"]),
        "artifacts_total": len(inventory),
    }


@app.get("/api/v1/artifacts", tags=["system"])
def list_artifacts() -> dict[str, Any]:
    """Every artifact the API can serve, and the command that produces each one."""
    return {"artifacts": store.inventory()}


@app.get("/api/v1/datasets", tags=["data"])
def list_datasets() -> dict[str, Any]:
    """Datasets that have been built into this working directory."""
    analytical_store = LocalAnalyticalStore(store.base_dir / "data")
    resolver = DatasetUniverseResolver(analytical_store)

    datasets: list[dict[str, Any]] = []
    data_dir = store.base_dir / "data"
    if data_dir.is_dir():
        for candidate in sorted(data_dir.iterdir()):
            if not candidate.is_dir() or not (candidate / "instruments").is_dir():
                continue
            try:
                members = resolver.members(candidate.name)
            except Exception:  # noqa: BLE001 - an unreadable roster is reported, not fatal
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
    return {"datasets": datasets}


def _serve(key: str) -> dict[str, Any]:
    try:
        return store.load(key)
    except ArtifactNotFound as err:
        raise HTTPException(
            status_code=404,
            detail={
                "error": f"{key} has not been produced yet",
                "expected_path": str(err.path),
                "produce_with": err.command,
            },
        ) from err


@app.get("/api/v1/factor-research", tags=["research"])
def factor_research() -> dict[str, Any]:
    """Latest single-factor research report."""
    return _serve("factor-research")


@app.get("/api/v1/backtest", tags=["research"])
def backtest() -> dict[str, Any]:
    """Latest backtest manifest, including the equity curve and benchmark comparison."""
    return _serve("backtest")


@app.get("/api/v1/validation", tags=["research"])
def validation() -> dict[str, Any]:
    """Latest falsification report and lifecycle verdict."""
    return _serve("validation")


@app.get("/api/v1/models/comparison", tags=["research"])
def model_comparison() -> dict[str, Any]:
    """Latest purged walk-forward model comparison."""
    return _serve("model-comparison")


@app.get("/api/v1/market-data/verification", tags=["data"])
def market_data_verification() -> dict[str, Any]:
    """Corporate-action adjustment checked against the data provider's own series."""
    return _serve("market-data-verification")


@app.get("/api/v1/research-report", tags=["research"])
def research_report() -> dict[str, Any]:
    """Latest signed research campaign report."""
    return _serve("research-report")


@app.get("/api/v1/paper/evidence", tags=["operations"])
def paper_evidence() -> dict[str, Any]:
    """Latest paper trading forward evidence."""
    return _serve("paper-forward-evidence")
