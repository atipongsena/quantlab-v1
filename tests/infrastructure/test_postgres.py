from __future__ import annotations

import pytest

from migrations.env import rollback_migration, run_migrations
from quantlab.common.errors import QuantLabError
from quantlab.infrastructure.db import DatabaseConfig, DatabaseEngine


def test_schema_migration_roundtrip() -> None:
    engine = DatabaseEngine(DatabaseConfig(url="sqlite:///:memory:"))

    # Run migration forward
    applied = run_migrations(engine)
    assert "0001_foundation" in applied

    # Verify tables exist
    with engine.transaction() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        table_names = {row[0] for row in cursor.fetchall()}
        assert "jobs" in table_names
        assert "artifacts_meta" in table_names
        assert "schema_migrations" in table_names

    # Rollback migration
    rollback_migration(engine, "0001_foundation")

    # Verify tables removed
    with engine.transaction() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        table_names = {row[0] for row in cursor.fetchall()}
        assert "jobs" not in table_names
        assert "artifacts_meta" not in table_names


def test_transaction_rollback_on_error() -> None:
    engine = DatabaseEngine(DatabaseConfig(url="sqlite:///:memory:"))
    run_migrations(engine)

    with pytest.raises(QuantLabError, match="Transaction rolled back"):
        with engine.transaction() as conn:
            conn.execute(
                "INSERT INTO schema_migrations (version, applied_at) VALUES ('v_test', 'now')"
            )
            raise RuntimeError("Forced simulation error")

    # Ensure insert was rolled back
    with engine.transaction() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM schema_migrations WHERE version = 'v_test'")
        assert cursor.fetchone() is None
