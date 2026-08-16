from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType
from typing import Protocol

from quantlab.common.clock import require_utc
from quantlab.common.config import JsonValue
from quantlab.common.errors import QuantLabError


class ArtifactIntegrityError(QuantLabError):
    """Raised when an artifact's content does not match its recorded hash."""


class ArtifactStorageError(QuantLabError):
    """Raised when an artifact cannot be stored or accessed safely."""


@dataclass(frozen=True, slots=True)
class ArtifactRef:
    artifact_id: str
    kind: str
    uri: str
    content_hash: str
    byte_count: int
    created_at: datetime
    metadata: MappingProxyType[str, JsonValue]


class ArtifactStore(Protocol):
    def put_bytes(
        self,
        kind: str,
        payload: bytes,
        metadata: Mapping[str, JsonValue] | None = None,
    ) -> ArtifactRef: ...

    def get_verified(self, ref: ArtifactRef) -> bytes: ...

    def exists(self, ref: ArtifactRef) -> bool: ...


class LocalArtifactStore:
    def __init__(self, root_dir: Path) -> None:
        self._root_dir = root_dir.resolve()
        self._root_dir.mkdir(parents=True, exist_ok=True)

    @property
    def root_dir(self) -> Path:
        return self._root_dir

    def put_bytes(
        self,
        kind: str,
        payload: bytes,
        metadata: Mapping[str, JsonValue] | None = None,
    ) -> ArtifactRef:
        if not kind:
            raise ValueError("kind must be a nonempty string")
        if not isinstance(payload, bytes):
            raise TypeError("payload must be bytes")

        content_hash = hashlib.sha256(payload).hexdigest()
        byte_count = len(payload)
        now = datetime.now(UTC)
        meta = MappingProxyType(dict(metadata) if metadata is not None else {})

        artifact_rel_path = Path(kind) / f"{content_hash}.bin"
        target_path = (self._root_dir / artifact_rel_path).resolve()

        self._ensure_safe_path(target_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        if target_path.exists():
            existing_bytes = target_path.read_bytes()
            if existing_bytes != payload:
                raise ArtifactIntegrityError(
                    f"Artifact collision or mutation detected at {target_path}"
                )
        else:
            target_path.write_bytes(payload)

        return ArtifactRef(
            artifact_id=content_hash,
            kind=kind,
            uri=target_path.as_posix(),
            content_hash=content_hash,
            byte_count=byte_count,
            created_at=now,
            metadata=meta,
        )

    def get_verified(self, ref: ArtifactRef) -> bytes:
        target_path = Path(ref.uri).resolve()
        self._ensure_safe_path(target_path)

        if not target_path.is_file():
            raise ArtifactStorageError(f"Artifact file not found: {target_path}")

        payload = target_path.read_bytes()
        actual_hash = hashlib.sha256(payload).hexdigest()
        if actual_hash != ref.content_hash:
            raise ArtifactIntegrityError(
                f"Artifact hash mismatch: expected {ref.content_hash}, got {actual_hash}"
            )
        if len(payload) != ref.byte_count:
            raise ArtifactIntegrityError(
                f"Artifact size mismatch: expected {ref.byte_count}, got {len(payload)}"
            )

        require_utc(ref.created_at)
        return payload

    def exists(self, ref: ArtifactRef) -> bool:
        target_path = Path(ref.uri).resolve()
        try:
            self._ensure_safe_path(target_path)
            return target_path.is_file()
        except ArtifactStorageError:
            return False

    def _ensure_safe_path(self, path: Path) -> None:
        resolved = path.resolve()
        try:
            resolved.relative_to(self._root_dir)
        except ValueError as err:
            raise ArtifactStorageError(
                f"Path traversal detected: {path} is outside {self._root_dir}"
            ) from err
