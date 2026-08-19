"""Reads the evidence artifacts the CLI writes.

The API deliberately serves recorded runs rather than starting them. A thirty-year
backtest takes minutes and produces a signed artifact; re-running it inside a request
would both time out and break the property that a published number came from a specific,
hashed run. Producing evidence is the CLI's job, serving it is this layer's.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class ArtifactNotFound(Exception):
    """Raised when a requested artifact has not been produced yet."""

    def __init__(self, name: str, path: Path, command: str) -> None:
        self.name = name
        self.path = path
        self.command = command
        super().__init__(f"No {name} artifact at {path}. Produce it with: {command}")


@dataclass(frozen=True, slots=True)
class ArtifactSpec:
    key: str
    relative_path: str
    produced_by: str
    description: str


ARTIFACTS: tuple[ArtifactSpec, ...] = (
    ArtifactSpec(
        key="factor-research",
        relative_path="artifacts/latest/factor-research.json",
        produced_by="quantlab factor research momentum_12_1 --dataset DATASET-US-30Y-v001",
        description="Cross-sectional IC, decay, and quantile diagnostics for one factor",
    ),
    ArtifactSpec(
        key="backtest",
        relative_path="artifacts/latest/backtest/manifest.json",
        produced_by=(
            "quantlab backtest run configs/strategies/us-price-composite-v1.yaml "
            "--dataset DATASET-US-30Y-v001"
        ),
        description="Event-driven backtest metrics, equity curve, and benchmark comparison",
    ),
    ArtifactSpec(
        key="validation",
        relative_path="artifacts/latest/validation-report.json",
        produced_by="quantlab validate run configs/validation/default-v1.yaml",
        description="Falsification gates, robustness sweeps, bootstrap, and verdict",
    ),
    ArtifactSpec(
        key="model-comparison",
        relative_path="artifacts/latest/model-comparison.json",
        produced_by="quantlab model compare --dataset DATASET-US-30Y-v001",
        description="Purged walk-forward comparison of the baseline against ranking models",
    ),
    ArtifactSpec(
        key="market-data-verification",
        relative_path="artifacts/latest/market-data-verification.json",
        produced_by="python scripts/verify_market_data.py --fixture us_research",
        description="Engine corporate-action adjustment checked against the provider series",
    ),
    ArtifactSpec(
        key="research-report",
        relative_path="artifacts/latest/research-report.json",
        produced_by="quantlab campaign run configs/campaigns/quality-improves-momentum-v1.yaml",
        description="Signed multi-agent research campaign report",
    ),
    ArtifactSpec(
        key="paper-forward-evidence",
        relative_path="artifacts/latest/paper-forward-evidence.json",
        produced_by="quantlab paper simulate --deployment PAPER-SYNTHETIC",
        description="Paper trading forward evidence and reconciliation drift",
    ),
)

_BY_KEY = {spec.key: spec for spec in ARTIFACTS}


class ArtifactStore:
    """Locates and loads evidence artifacts under a repository root."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = Path(base_dir or Path.cwd())

    def spec(self, key: str) -> ArtifactSpec | None:
        return _BY_KEY.get(key)

    def path(self, key: str) -> Path:
        spec = _BY_KEY[key]
        return self.base_dir / spec.relative_path

    def load(self, key: str) -> dict[str, Any]:
        spec = _BY_KEY.get(key)
        if spec is None:
            raise KeyError(key)

        path = self.path(key)
        if not path.is_file():
            raise ArtifactNotFound(spec.key, path, spec.produced_by)

        with open(path, encoding="utf-8") as handle:
            payload: dict[str, Any] = json.load(handle)

        stat = path.stat()
        payload["_artifact"] = {
            "key": spec.key,
            "path": spec.relative_path,
            "produced_by": spec.produced_by,
            "generated_at": datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
            "bytes": stat.st_size,
        }
        return payload

    def inventory(self) -> list[dict[str, Any]]:
        """List every artifact the API can serve and whether it exists yet."""
        rows: list[dict[str, Any]] = []
        for spec in ARTIFACTS:
            path = self.path(spec.key)
            exists = path.is_file()
            rows.append(
                {
                    "key": spec.key,
                    "description": spec.description,
                    "path": spec.relative_path,
                    "produced_by": spec.produced_by,
                    "available": exists,
                    "generated_at": (
                        datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).isoformat()
                        if exists
                        else None
                    ),
                }
            )
        return rows
