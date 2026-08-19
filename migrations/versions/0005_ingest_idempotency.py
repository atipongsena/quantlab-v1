from __future__ import annotations

import sqlite3

VERSION = "0005_ingest_idempotency"
DESCRIPTION = "Make fundamental ingestion idempotent with a natural-key unique index"


def upgrade(conn: sqlite3.Connection) -> None:
    # Re-running `quantlab dataset build` must be a no-op, not an append. Without this,
    # a second build doubles every filing, and any metric read as-of a date silently
    # picks one of two identical rows while restatement history reports twice the
    # revisions that actually happened.
    conn.executescript(
        """
        DELETE FROM fundamentals
        WHERE id NOT IN (
            SELECT MIN(id) FROM fundamentals
            GROUP BY instrument_id, period_end, filing_date, available_at, metric, value
        );

        CREATE UNIQUE INDEX IF NOT EXISTS uq_fundamentals_natural_key
        ON fundamentals(
            instrument_id, period_end, filing_date, available_at, metric, value
        );
        """
    )


def downgrade(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DROP INDEX IF EXISTS uq_fundamentals_natural_key;
        """
    )
