from __future__ import annotations

import sqlite3

VERSION = "0003_fundamentals"
DESCRIPTION = "Create fundamentals table for bi-temporal point-in-time filings and restatements"


def upgrade(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS fundamentals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            instrument_id TEXT NOT NULL,
            period_end TEXT NOT NULL,
            filing_date TEXT NOT NULL,
            available_at TEXT NOT NULL,
            metric TEXT NOT NULL,
            value TEXT NOT NULL,
            is_restatement INTEGER NOT NULL DEFAULT 0,
            source TEXT NOT NULL,
            FOREIGN KEY(instrument_id) REFERENCES instruments(instrument_id)
        );

        CREATE INDEX IF NOT EXISTS idx_fundamentals_pit
        ON fundamentals(instrument_id, metric, available_at, period_end);
        """
    )


def downgrade(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DROP TABLE IF EXISTS fundamentals;
        """
    )
