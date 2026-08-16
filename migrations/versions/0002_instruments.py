from __future__ import annotations

import sqlite3

VERSION = "0002_instruments"
DESCRIPTION = "Create instruments and symbol_history tables"


def upgrade(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS instruments (
            instrument_id TEXT PRIMARY KEY,
            issuer_name TEXT NOT NULL,
            security_name TEXT NOT NULL,
            instrument_type TEXT NOT NULL,
            exchange TEXT NOT NULL,
            currency TEXT NOT NULL,
            active_from TEXT NOT NULL,
            active_to TEXT,
            status TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS instrument_symbol_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            instrument_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            exchange TEXT NOT NULL,
            valid_from TEXT NOT NULL,
            valid_to TEXT,
            source TEXT NOT NULL,
            FOREIGN KEY(instrument_id) REFERENCES instruments(instrument_id)
        );

        CREATE INDEX IF NOT EXISTS idx_symbol_lookup 
        ON instrument_symbol_history(symbol, exchange, valid_from, valid_to);
        """
    )


def downgrade(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DROP TABLE IF EXISTS instrument_symbol_history;
        DROP TABLE IF EXISTS instruments;
        """
    )
