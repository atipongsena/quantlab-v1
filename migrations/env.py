from __future__ import annotations

import importlib
from datetime import UTC, datetime
from typing import Any

from quantlab.infrastructure.db import DatabaseEngine

m0001: Any = importlib.import_module("migrations.versions.0001_foundation")


def run_migrations(engine: DatabaseEngine) -> list[str]:
    applied: list[str] = []
    with engine.transaction() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL
            )
            """
        )
        cursor = conn.cursor()
        cursor.execute("SELECT version FROM schema_migrations")
        existing_versions = {row[0] for row in cursor.fetchall()}

        if m0001.VERSION not in existing_versions:
            m0001.upgrade(conn)
            now = datetime.now(UTC).isoformat()
            cursor.execute(
                "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                (m0001.VERSION, now),
            )
            applied.append(m0001.VERSION)

    return applied


def rollback_migration(engine: DatabaseEngine, version: str) -> None:
    with engine.transaction() as conn:
        if version == m0001.VERSION:
            m0001.downgrade(conn)
            conn.execute("DELETE FROM schema_migrations WHERE version = ?", (version,))
