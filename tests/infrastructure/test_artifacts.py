from __future__ import annotations

from pathlib import Path

import pytest

from quantlab.infrastructure.artifacts import (
    ArtifactIntegrityError,
    ArtifactRef,
    ArtifactStorageError,
    LocalArtifactStore,
)


def test_artifact_content_addressing_and_immutability(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")
    payload = b"test payload 12345"

    ref1 = store.put_bytes(kind="models", payload=payload, metadata={"name": "model_v1"})
    assert ref1.byte_count == len(payload)
    assert store.exists(ref1)

    # Identical put returns same ref without corruption
    ref2 = store.put_bytes(kind="models", payload=payload, metadata={"name": "model_v1"})
    assert ref1.content_hash == ref2.content_hash

    # Verification retrieves exact bytes
    retrieved = store.get_verified(ref1)
    assert retrieved == payload


def test_artifact_path_traversal_rejection(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")

    # Path traversal in ref URI
    invalid_ref = ArtifactRef(
        artifact_id="malicious",
        kind="test",
        uri=(tmp_path.parent / "secret.txt").as_posix(),
        content_hash="abc",
        byte_count=10,
        created_at=store.put_bytes(kind="test", payload=b"ok").created_at,
        metadata=store.put_bytes(kind="test", payload=b"ok").metadata,
    )

    with pytest.raises(ArtifactStorageError, match="Path traversal"):
        store.get_verified(invalid_ref)


def test_artifact_tamper_detection(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")
    payload = b"original data"
    ref = store.put_bytes(kind="data", payload=payload)

    # Tamper with file on disk
    Path(ref.uri).write_bytes(b"tampered data")

    with pytest.raises(ArtifactIntegrityError, match="hash mismatch"):
        store.get_verified(ref)
