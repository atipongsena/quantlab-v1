from __future__ import annotations

from datetime import date
from pathlib import Path

from quantlab.data.ingestion import IngestionService
from quantlab.data.providers import SyntheticFixtureProvider
from quantlab.data.raw_snapshots import RawSnapshotStore
from quantlab.infrastructure.artifacts import LocalArtifactStore


def test_raw_snapshot_store_immutability_and_roundtrip(tmp_path: Path) -> None:
    artifact_store = LocalArtifactStore(tmp_path)
    store = RawSnapshotStore(artifact_store)

    ref = store.store(
        provider_name="test_provider",
        dataset="test_dataset",
        fetch_params={"symbols": ["AAPL"], "year": 2020},
        payload=b"raw,csv,payload\n1,2,3\n",
    )

    assert ref.provider_name == "test_provider"
    assert ref.dataset == "test_dataset"
    assert len(ref.content_hash) == 64

    # Verify retrieval
    retrieved = store.get(ref)
    assert retrieved == b"raw,csv,payload\n1,2,3\n"


def test_ingestion_service_eod_flow(tmp_path: Path) -> None:
    artifact_store = LocalArtifactStore(tmp_path)
    snapshot_store = RawSnapshotStore(artifact_store)
    provider = SyntheticFixtureProvider(fixture_dir="data/fixtures/synthetic_v1/source")
    service = IngestionService(provider, snapshot_store)

    result = service.ingest_eod(
        symbols=["AAPL"],
        start_date=date(2020, 1, 1),
        end_date=date(2020, 1, 31),
    )

    assert result.status == "SUCCESS"
    assert result.row_count > 0
    assert result.snapshot_ref.dataset == "prices"


def test_ingestion_service_handles_provider_failure(tmp_path: Path) -> None:
    artifact_store = LocalArtifactStore(tmp_path)
    snapshot_store = RawSnapshotStore(artifact_store)
    provider = SyntheticFixtureProvider(
        fixture_dir="data/fixtures/synthetic_v1/source",
        rate_limit_failure_count=99,
    )
    service = IngestionService(provider, snapshot_store)

    result = service.ingest_eod(
        symbols=["AAPL"],
        start_date=date(2020, 1, 1),
        end_date=date(2020, 1, 31),
    )

    assert result.status == "FAILED"
    assert len(result.errors) > 0
