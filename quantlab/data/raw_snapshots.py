from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from quantlab.common.hashing import canonical_hash
from quantlab.infrastructure.artifacts import ArtifactRef, LocalArtifactStore


@dataclass(frozen=True, slots=True)
class SnapshotRef:
    snapshot_id: str
    provider_name: str
    dataset: str
    fetch_params: dict[str, object]
    artifact_ref: ArtifactRef
    content_hash: str
    created_at: datetime


class RawSnapshotStore:
    def __init__(self, artifact_store: LocalArtifactStore) -> None:
        self._artifact_store = artifact_store

    def store(
        self,
        provider_name: str,
        dataset: str,
        fetch_params: Mapping[str, object],
        payload: bytes,
    ) -> SnapshotRef:
        kind = f"raw_snapshots/{provider_name}/{dataset}"
        artifact_ref = self._artifact_store.put_bytes(kind=kind, payload=payload)
        now = datetime.now(UTC)
        content_hash = canonical_hash(
            {
                "artifact_sha256": artifact_ref.content_hash,
                "provider": provider_name,
                "dataset": dataset,
                "fetch_params": dict(fetch_params),
            }
        )
        snapshot_id = f"snap_{uuid4().hex[:12]}"
        return SnapshotRef(
            snapshot_id=snapshot_id,
            provider_name=provider_name,
            dataset=dataset,
            fetch_params=dict(fetch_params),
            artifact_ref=artifact_ref,
            content_hash=content_hash,
            created_at=now,
        )

    def get(self, ref: SnapshotRef) -> bytes:
        return self._artifact_store.get_verified(ref.artifact_ref)
