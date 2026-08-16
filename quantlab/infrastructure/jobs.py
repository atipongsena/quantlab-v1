from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Protocol
from uuid import uuid4

from quantlab.common.clock import require_utc
from quantlab.common.config import JsonValue
from quantlab.common.errors import QuantLabError


class JobError(QuantLabError):
    """Raised when job operations fail."""


class JobStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True, slots=True)
class JobRecord:
    job_id: str
    job_type: str
    idempotency_key: str
    status: JobStatus
    payload: MappingProxyType[str, JsonValue]
    result: MappingProxyType[str, JsonValue] | None
    error: str | None
    created_at: datetime
    updated_at: datetime


class JobRepository(Protocol):
    def create_once(
        self,
        job_type: str,
        idempotency_key: str,
        payload: Mapping[str, JsonValue],
    ) -> JobRecord: ...

    def get_by_id(self, job_id: str) -> JobRecord | None: ...

    def get_by_idempotency_key(self, job_type: str, idempotency_key: str) -> JobRecord | None: ...

    def update_status(
        self,
        job_id: str,
        status: JobStatus,
        result: Mapping[str, JsonValue] | None = None,
        error: str | None = None,
    ) -> JobRecord: ...


class InMemoryJobRepository:
    def __init__(self) -> None:
        self._jobs_by_id: dict[str, JobRecord] = {}
        self._index: dict[tuple[str, str], str] = {}

    def create_once(
        self,
        job_type: str,
        idempotency_key: str,
        payload: Mapping[str, JsonValue],
    ) -> JobRecord:
        if not job_type or not idempotency_key:
            raise ValueError("job_type and idempotency_key must be nonempty")

        key = (job_type, idempotency_key)
        if key in self._index:
            existing_id = self._index[key]
            return self._jobs_by_id[existing_id]

        now = datetime.now(UTC)
        job_id = str(uuid4())
        record = JobRecord(
            job_id=job_id,
            job_type=job_type,
            idempotency_key=idempotency_key,
            status=JobStatus.PENDING,
            payload=MappingProxyType(dict(payload)),
            result=None,
            error=None,
            created_at=now,
            updated_at=now,
        )
        self._jobs_by_id[job_id] = record
        self._index[key] = job_id
        return record

    def get_by_id(self, job_id: str) -> JobRecord | None:
        return self._jobs_by_id.get(job_id)

    def get_by_idempotency_key(self, job_type: str, idempotency_key: str) -> JobRecord | None:
        key = (job_type, idempotency_key)
        job_id = self._index.get(key)
        if job_id is None:
            return None
        return self._jobs_by_id.get(job_id)

    def update_status(
        self,
        job_id: str,
        status: JobStatus,
        result: Mapping[str, JsonValue] | None = None,
        error: str | None = None,
    ) -> JobRecord:
        existing = self._jobs_by_id.get(job_id)
        if existing is None:
            raise JobError(f"Job not found: {job_id}")

        now = datetime.now(UTC)
        updated = JobRecord(
            job_id=existing.job_id,
            job_type=existing.job_type,
            idempotency_key=existing.idempotency_key,
            status=status,
            payload=existing.payload,
            result=MappingProxyType(dict(result)) if result is not None else existing.result,
            error=error if error is not None else existing.error,
            created_at=existing.created_at,
            updated_at=now,
        )
        require_utc(updated.updated_at)
        self._jobs_by_id[job_id] = updated
        return updated
