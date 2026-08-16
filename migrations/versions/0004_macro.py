from __future__ import annotations

import sqlite3

VERSION = "0004_macro"
DESCRIPTION = "Create macro_vintages table for PIT macroeconomic indicators"


def upgrade(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS macro_vintages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            series_id TEXT NOT NULL,
            period_date TEXT NOT NULL,
            release_time TEXT NOT NULL,
            value TEXT NOT NULL,
            source TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_macro_pit
        ON macro_vintages(series_id, release_time, period_date);
        """
    )


def downgrade(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DROP TABLE IF EXISTS macro_vintages;
        """
    )
