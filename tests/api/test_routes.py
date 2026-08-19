"""Tests for the REST API that serves evidence artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

fastapi = pytest.importorskip(
    "fastapi",
    reason='API extra not installed; run pip install -e ".[api]"',
)
from fastapi.testclient import TestClient  # noqa: E402

from apps.api.app import app, store  # noqa: E402


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(store, "base_dir", tmp_path)
    return TestClient(app)


def test_health_reports_artifact_availability(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["artifacts_available"] == 0
    assert payload["artifacts_total"] > 0


def test_openapi_schema_is_served(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    assert schema["openapi"].startswith("3.1")
    assert "/api/v1/backtest" in schema["paths"]


def test_missing_artifact_returns_the_command_that_produces_it(client: TestClient) -> None:
    """A missing artifact is a 404 that tells you what to run.

    Returning a plausible-looking empty payload instead is how a dashboard ends up
    showing zeros that nobody realises are placeholders.
    """
    response = client.get("/api/v1/backtest")
    assert response.status_code == 404
    detail = response.json()["detail"]
    assert "quantlab backtest run" in detail["produce_with"]
    assert detail["expected_path"].endswith("manifest.json")


def test_artifact_is_served_with_provenance(client: TestClient, tmp_path: Path) -> None:
    target = tmp_path / "artifacts" / "latest" / "backtest" / "manifest.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"strategy_id": "demo", "metrics": {}}), encoding="utf-8")

    payload = client.get("/api/v1/backtest").json()
    assert payload["strategy_id"] == "demo"
    assert payload["_artifact"]["path"].endswith("manifest.json")
    assert "quantlab backtest run" in payload["_artifact"]["produced_by"]


def test_datasets_endpoint_reports_nothing_when_none_are_built(client: TestClient) -> None:
    assert client.get("/api/v1/datasets").json() == {"datasets": []}


def test_artifact_inventory_lists_every_producer(client: TestClient) -> None:
    rows = client.get("/api/v1/artifacts").json()["artifacts"]
    assert rows
    assert all(row["produced_by"] for row in rows)
    assert all(row["available"] is False for row in rows)
