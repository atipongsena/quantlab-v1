"""SQLite-backed paper trading state store and schema management."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from quantlab.domain.identity import InstrumentId
from quantlab.paper.contracts import BrokerAccount, PaperFill


class PaperStateStore:
    """Persistent storage for paper accounts, positions, orders, and fills."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        conn = self._get_connection()
        try:
            with conn:
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS paper_accounts (
                        account_id TEXT PRIMARY KEY,
                        cash_balance TEXT NOT NULL,
                        buying_power TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS paper_positions (
                        account_id TEXT NOT NULL,
                        instrument_id TEXT NOT NULL,
                        quantity TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        PRIMARY KEY (account_id, instrument_id)
                    );

                    CREATE TABLE IF NOT EXISTS paper_orders (
                        order_id TEXT PRIMARY KEY,
                        session TEXT NOT NULL,
                        instrument_id TEXT NOT NULL,
                        side TEXT NOT NULL,
                        quantity INTEGER NOT NULL,
                        order_type TEXT NOT NULL,
                        status TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS paper_fills (
                        fill_id TEXT PRIMARY KEY,
                        order_id TEXT NOT NULL,
                        instrument_id TEXT NOT NULL,
                        side TEXT NOT NULL,
                        quantity INTEGER NOT NULL,
                        price TEXT NOT NULL,
                        commission TEXT NOT NULL,
                        filled_at TEXT NOT NULL
                    );
                    """
                )
        finally:
            conn.close()

    def save_account(self, account: BrokerAccount) -> None:
        now_str = datetime.now(tz=UTC).isoformat()
        conn = self._get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO paper_accounts (account_id, cash_balance, buying_power, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(account_id) DO UPDATE SET
                        cash_balance=excluded.cash_balance,
                        buying_power=excluded.buying_power,
                        updated_at=excluded.updated_at
                    """,
                    (
                        account.account_id,
                        str(account.cash_balance),
                        str(account.buying_power),
                        now_str,
                    ),
                )
                conn.execute(
                    "DELETE FROM paper_positions WHERE account_id = ?",
                    (account.account_id,),
                )
                for inst, qty in account.positions.items():
                    conn.execute(
                        """
                        INSERT INTO paper_positions (account_id, instrument_id, quantity, updated_at)
                        VALUES (?, ?, ?, ?)
                        """,
                        (account.account_id, str(inst.value), str(qty), now_str),
                    )
        finally:
            conn.close()

    def load_account(self, account_id: str) -> BrokerAccount | None:
        conn = self._get_connection()
        try:
            cur = conn.execute(
                "SELECT cash_balance, buying_power FROM paper_accounts WHERE account_id = ?",
                (account_id,),
            )
            row = cur.fetchone()
            if not row:
                return None

            pos_cur = conn.execute(
                "SELECT instrument_id, quantity FROM paper_positions WHERE account_id = ?",
                (account_id,),
            )
            positions: dict[InstrumentId, Decimal] = {
                InstrumentId(uuid.UUID(p_row["instrument_id"])): Decimal(p_row["quantity"])
                for p_row in pos_cur.fetchall()
            }

            return BrokerAccount(
                account_id=account_id,
                cash_balance=Decimal(row["cash_balance"]),
                buying_power=Decimal(row["buying_power"]),
                positions=positions,
            )
        finally:
            conn.close()

    def record_fill(self, fill: PaperFill) -> None:
        conn = self._get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO paper_fills (
                        fill_id, order_id, instrument_id, side, quantity, price, commission, filled_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(fill_id) DO NOTHING
                    """,
                    (
                        fill.fill_id,
                        fill.order_id,
                        str(fill.instrument_id.value),
                        fill.side.value,
                        fill.quantity,
                        str(fill.price),
                        str(fill.commission),
                        fill.filled_at.isoformat(),
                    ),
                )
        finally:
            conn.close()
