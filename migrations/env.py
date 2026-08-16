from __future__ import annotations

import importlib
from datetime import UTC, datetime
from typing import Any

from quantlab.infrastructure.db import DatabaseEngine

MIGRATIONS: list[tuple[str, Any]] = [
    ("0001_foundation", importlib.import_module("migrations.versions.0001_foundation")),
    ("0002_instruments", importlib.import_module("migrations.versions.0002_instruments")),
    ("0003_fundamentals", importlib.import_module("migrations.versions.0003_fundamentals")),
]


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

        for version, mod in MIGRATIONS:
            if version not in existing_versions:
                mod.upgrade(conn)
                now = datetime.now(UTC).isoformat()
                cursor.execute(
                    "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                    (version, now),
                )
                applied.append(version)

    return applied


def rollback_migration(engine: DatabaseEngine, version: str) -> None:
    with engine.transaction() as conn:
        for v, mod in reversed(MIGRATIONS):
            if v == version:
                mod.downgrade(conn)
                conn.execute("DELETE FROM schema_migrations WHERE version = ?", (version,))
                break
