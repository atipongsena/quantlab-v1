"""Tests for REST API application endpoints and OpenAPI specification."""

from apps.api.app import QuantLabAPI


def test_api_health_endpoint() -> None:
    api = QuantLabAPI()
    code, resp = api.handle("GET", "/health")
    assert code == 200
    assert resp["status"] == "ok"


def test_api_openapi_spec_endpoint() -> None:
    api = QuantLabAPI()
    code, resp = api.handle("GET", "/api/v1/openapi.json")
    assert code == 200
    assert resp["openapi"] == "3.1.0"
    assert "/health" in resp["paths"]  # type: ignore[operator]


def test_api_datasets_and_research_endpoints() -> None:
    api = QuantLabAPI()
    code_ds, resp_ds = api.handle("GET", "/api/v1/datasets")
    assert code_ds == 200
    assert "datasets" in resp_ds

    code_res, resp_res = api.handle(
        "POST", "/api/v1/factors/research", {"factor_name": "momentum_12_1"}
    )
    assert code_res == 200
    assert resp_res["factor_name"] == "momentum_12_1"
    assert resp_res["mean_ic"] > 0
