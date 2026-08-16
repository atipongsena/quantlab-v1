from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from datetime import UTC, datetime
from types import MappingProxyType
from uuid import uuid4

from quantlab.common.config import JsonValue
from quantlab.common.errors import QuantLabError
from quantlab.infrastructure.db import DatabaseEngine
from quantlab.infrastructure.jobs import JobRecord, JobRepository, JobStatus


class RepositoryError(QuantLabError):
    """Raised when repository queries fail."""


class SqlJobRepository(JobRepository):
    def __init__(self, engine: DatabaseEngine) -> None:
        self._engine = engine

    def create_once(
        self,
        job_type: str,
        idempotency_key: str,
        payload: Mapping[str, JsonValue],
    ) -> JobRecord:
        if not job_type or not idempotency_key:
            raise ValueError("job_type and idempotency_key must be nonempty")

        with self._engine.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM jobs WHERE job_type = ? AND idempotency_key = ?",
                (job_type, idempotency_key),
            )
            row = cursor.fetchone()
            if row is not None:
                return self._row_to_record(row)

            now = datetime.now(UTC).isoformat()
            job_id = str(uuid4())
            payload_json = json.dumps(payload, sort_keys=True)
            cursor.execute(
                """
                INSERT INTO jobs (
                    job_id, job_type, idempotency_key, status,
                    payload_json, result_json, error, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, NULL, NULL, ?, ?)
                """,
                (
                    job_id,
                    job_type,
                    idempotency_key,
                    JobStatus.PENDING.value,
                    payload_json,
                    now,
                    now,
                ),
            )

            return JobRecord(
                job_id=job_id,
                job_type=job_type,
                idempotency_key=idempotency_key,
                status=JobStatus.PENDING,
                payload=MappingProxyType(dict(payload)),
                result=None,
                error=None,
                created_at=datetime.fromisoformat(now),
                updated_at=datetime.fromisoformat(now),
            )

    def get_by_id(self, job_id: str) -> JobRecord | None:
        with self._engine.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
            row = cursor.fetchone()
            return self._row_to_record(row) if row is not None else None

    def get_by_idempotency_key(self, job_type: str, idempotency_key: str) -> JobRecord | None:
        with self._engine.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM jobs WHERE job_type = ? AND idempotency_key = ?",
                (job_type, idempotency_key),
            )
            row = cursor.fetchone()
            return self._row_to_record(row) if row is not None else None

    def update_status(
        self,
        job_id: str,
        status: JobStatus,
        result: Mapping[str, JsonValue] | None = None,
        error: str | None = None,
    ) -> JobRecord:
        with self._engine.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
            row = cursor.fetchone()
            if row is None:
                raise RepositoryError(f"Job not found: {job_id}")

            now = datetime.now(UTC).isoformat()
            result_json = json.dumps(result, sort_keys=True) if result is not None else None

            cursor.execute(
                """
                UPDATE jobs
                SET status = ?, result_json = COALESCE(?, result_json),
                    error = COALESCE(?, error), updated_at = ?
                WHERE job_id = ?
                """,
                (status.value, result_json, error, now, job_id),
            )

            cursor.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
            updated_row = cursor.fetchone()
            assert updated_row is not None
            return self._row_to_record(updated_row)

    def _row_to_record(self, row: dict[str, object] | sqlite3.Row) -> JobRecord:
        row_dict = dict(row)
        payload = json.loads(str(row_dict["payload_json"]))
        result_raw = row_dict.get("result_json")
        result = json.loads(str(result_raw)) if result_raw else None
        error = str(row_dict["error"]) if row_dict.get("error") is not None else None

        return JobRecord(
            job_id=str(row_dict["job_id"]),
            job_type=str(row_dict["job_type"]),
            idempotency_key=str(row_dict["idempotency_key"]),
            status=JobStatus(str(row_dict["status"])),
            payload=MappingProxyType(payload),
            result=MappingProxyType(result) if result is not None else None,
            error=error,
            created_at=datetime.fromisoformat(str(row_dict["created_at"])),
            updated_at=datetime.fromisoformat(str(row_dict["updated_at"])),
        )
