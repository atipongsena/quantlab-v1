from __future__ import annotations

from migrations.env import run_migrations
from quantlab.infrastructure.db import DatabaseConfig, DatabaseEngine
from quantlab.infrastructure.jobs import InMemoryJobRepository, JobStatus
from quantlab.infrastructure.repositories import SqlJobRepository


def test_in_memory_job_repository_idempotency_and_state() -> None:
    repo = InMemoryJobRepository()

    job1 = repo.create_once("backtest", "idem-123", {"strategy": "momentum"})
    assert job1.status == JobStatus.PENDING

    # Second call with same idempotency key returns same job_id
    job2 = repo.create_once("backtest", "idem-123", {"strategy": "momentum_different_payload"})
    assert job2.job_id == job1.job_id

    # Update status
    updated = repo.update_status(job1.job_id, JobStatus.COMPLETED, result={"sharpe": 1.5})
    assert updated.status == JobStatus.COMPLETED
    assert updated.result is not None
    assert updated.result["sharpe"] == 1.5


def test_sql_job_repository_idempotency_and_state() -> None:
    engine = DatabaseEngine(DatabaseConfig(url="sqlite:///:memory:"))
    run_migrations(engine)
    repo = SqlJobRepository(engine)

    job1 = repo.create_once("ingestion", "idem-456", {"dataset": "synthetic"})
    assert job1.status == JobStatus.PENDING

    # Idempotent call
    job2 = repo.create_once("ingestion", "idem-456", {"dataset": "synthetic"})
    assert job2.job_id == job1.job_id

    # Lookup
    found = repo.get_by_id(job1.job_id)
    assert found is not None
    assert found.job_id == job1.job_id

    # Update
    updated = repo.update_status(job1.job_id, JobStatus.FAILED, error="Timeout error")
    assert updated.status == JobStatus.FAILED
    assert updated.error == "Timeout error"
