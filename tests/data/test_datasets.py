from __future__ import annotations

from pathlib import Path

from quantlab.data.datasets import DatasetPublisher
from quantlab.data.quality import QualityReport
from quantlab.infrastructure.analytical_store import LocalAnalyticalStore
from quantlab.infrastructure.artifacts import LocalArtifactStore


def test_dataset_publisher_manifest_and_artifact_immutability(tmp_path: Path) -> None:
    artifact_store = LocalArtifactStore(tmp_path / "artifacts")
    analytical_store = LocalAnalyticalStore(tmp_path / "data")

    publisher = DatasetPublisher(artifact_store, analytical_store)

    tables_data = {
        "prices": [
            {"symbol": "AAPL", "date": "2020-01-02", "close": "100.0"},
            {"symbol": "AAPL", "date": "2020-01-03", "close": "102.0"},
        ],
        "actions": [
            {"symbol": "AAPL", "effective_date": "2020-08-31", "ratio": "4.0"},
        ],
    }

    quality_report = QualityReport(
        dataset_id="test_ds",
        overall_status="PASS",
        checks=(),
        confidence_score=1.0,
    )

    manifest = publisher.publish(
        dataset_id="test_ds",
        version="v1",
        tables_data=tables_data,
        quality_report=quality_report,
    )

    assert manifest.dataset_id == "test_ds"
    assert manifest.version == "v1"
    assert "prices" in manifest.tables
    assert "actions" in manifest.tables
    assert manifest.row_counts["prices"] == 2
    assert manifest.row_counts["actions"] == 1
    assert len(manifest.manifest_hash) == 64
