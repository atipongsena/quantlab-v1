from __future__ import annotations

import csv
import io
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from uuid import uuid4

from quantlab.data.providers import DataProvider, retry_with_backoff
from quantlab.data.raw_snapshots import RawSnapshotStore, SnapshotRef


@dataclass(frozen=True, slots=True)
class IngestionJobResult:
    job_id: str
    snapshot_ref: SnapshotRef
    row_count: int
    status: str  # "SUCCESS", "FAILED"
    errors: tuple[str, ...] = ()


class IngestionService:
    def __init__(
        self,
        provider: DataProvider,
        snapshot_store: RawSnapshotStore,
    ) -> None:
        self._provider = provider
        self._snapshot_store = snapshot_store

    def ingest_eod(
        self,
        symbols: Sequence[str],
        start_date: date,
        end_date: date,
    ) -> IngestionJobResult:
        job_id = f"ingest_eod_{uuid4().hex[:10]}"
        try:
            payload = retry_with_backoff(
                lambda: self._provider.fetch_eod(symbols, start_date, end_date)
            )
            snapshot_ref = self._snapshot_store.store(
                provider_name=payload.provider_name,
                dataset=payload.dataset,
                fetch_params=payload.fetch_params,
                payload=payload.content,
            )

            # Count rows
            buf = io.StringIO(payload.content.decode("utf-8"))
            reader = csv.DictReader(buf)
            row_count = sum(1 for _ in reader)

            return IngestionJobResult(
                job_id=job_id,
                snapshot_ref=snapshot_ref,
                row_count=row_count,
                status="SUCCESS",
            )
        except Exception as err:
            dummy_ref = SnapshotRef(
                snapshot_id="",
                provider_name="",
                dataset="prices",
                fetch_params={},
                artifact_ref=None,  # type: ignore[arg-type]
                content_hash="",
                created_at=None,  # type: ignore[arg-type]
            )
            return IngestionJobResult(
                job_id=job_id,
                snapshot_ref=dummy_ref,
                row_count=0,
                status="FAILED",
                errors=(str(err),),
            )

    def ingest_actions(
        self,
        symbols: Sequence[str],
        start_date: date,
        end_date: date,
    ) -> IngestionJobResult:
        job_id = f"ingest_actions_{uuid4().hex[:10]}"
        try:
            payload = retry_with_backoff(
                lambda: self._provider.fetch_actions(symbols, start_date, end_date)
            )
            snapshot_ref = self._snapshot_store.store(
                provider_name=payload.provider_name,
                dataset=payload.dataset,
                fetch_params=payload.fetch_params,
                payload=payload.content,
            )

            buf = io.StringIO(payload.content.decode("utf-8"))
            reader = csv.DictReader(buf)
            row_count = sum(1 for _ in reader)

            return IngestionJobResult(
                job_id=job_id,
                snapshot_ref=snapshot_ref,
                row_count=row_count,
                status="SUCCESS",
            )
        except Exception as err:
            dummy_ref = SnapshotRef(
                snapshot_id="",
                provider_name="",
                dataset="actions",
                fetch_params={},
                artifact_ref=None,  # type: ignore[arg-type]
                content_hash="",
                created_at=None,  # type: ignore[arg-type]
            )
            return IngestionJobResult(
                job_id=job_id,
                snapshot_ref=dummy_ref,
                row_count=0,
                status="FAILED",
                errors=(str(err),),
            )

    def ingest_fundamentals(
        self,
        symbols: Sequence[str],
        start_date: date,
        end_date: date,
    ) -> IngestionJobResult:
        job_id = f"ingest_funds_{uuid4().hex[:10]}"
        try:
            payload = retry_with_backoff(
                lambda: self._provider.fetch_fundamentals(symbols, start_date, end_date)
            )
            snapshot_ref = self._snapshot_store.store(
                provider_name=payload.provider_name,
                dataset=payload.dataset,
                fetch_params=payload.fetch_params,
                payload=payload.content,
            )

            buf = io.StringIO(payload.content.decode("utf-8"))
            reader = csv.DictReader(buf)
            row_count = sum(1 for _ in reader)

            return IngestionJobResult(
                job_id=job_id,
                snapshot_ref=snapshot_ref,
                row_count=row_count,
                status="SUCCESS",
            )
        except Exception as err:
            dummy_ref = SnapshotRef(
                snapshot_id="",
                provider_name="",
                dataset="fundamentals",
                fetch_params={},
                artifact_ref=None,  # type: ignore[arg-type]
                content_hash="",
                created_at=None,  # type: ignore[arg-type]
            )
            return IngestionJobResult(
                job_id=job_id,
                snapshot_ref=dummy_ref,
                row_count=0,
                status="FAILED",
                errors=(str(err),),
            )
