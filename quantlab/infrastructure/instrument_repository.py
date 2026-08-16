from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Protocol
from uuid import UUID

from quantlab.data.instruments import InstrumentIdentityError, validate_non_overlapping_history
from quantlab.domain.identity import (
    Instrument,
    InstrumentId,
    InstrumentStatus,
    InstrumentType,
    SymbolHistory,
)
from quantlab.infrastructure.db import DatabaseEngine


class InstrumentRepository(Protocol):
    def resolve(self, symbol: str, exchange: str, as_of: date) -> InstrumentId | None: ...

    def history(self, instrument_id: InstrumentId) -> tuple[SymbolHistory, ...]: ...

    def get_instrument(self, instrument_id: InstrumentId) -> Instrument | None: ...

    def upsert_identity(
        self,
        source_record: Instrument,
        symbol_histories: Sequence[SymbolHistory] = (),
    ) -> Instrument: ...


class SqlInstrumentRepository(InstrumentRepository):
    def __init__(self, engine: DatabaseEngine) -> None:
        self._engine = engine

    def resolve(self, symbol: str, exchange: str, as_of: date) -> InstrumentId | None:
        as_of_str = as_of.isoformat()
        with self._engine.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT instrument_id FROM instrument_symbol_history
                WHERE symbol = ? AND exchange = ?
                  AND valid_from <= ? AND (valid_to IS NULL OR valid_to >= ?)
                """,
                (symbol.upper(), exchange.upper(), as_of_str, as_of_str),
            )
            rows = cursor.fetchall()
            if not rows:
                return None
            if len(rows) > 1:
                msg = (
                    f"Ambiguous resolution: multiple instruments for "
                    f"{symbol} on {exchange} as of {as_of}"
                )
                raise InstrumentIdentityError(msg)
            return InstrumentId.from_uuid(UUID(str(rows[0]["instrument_id"])))

    def history(self, instrument_id: InstrumentId) -> tuple[SymbolHistory, ...]:
        with self._engine.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT symbol, exchange, valid_from, valid_to, source
                FROM instrument_symbol_history
                WHERE instrument_id = ?
                ORDER BY valid_from
                """,
                (str(instrument_id.value),),
            )
            rows = cursor.fetchall()
            histories = [
                SymbolHistory(
                    instrument_id=instrument_id,
                    symbol=str(row["symbol"]),
                    exchange=str(row["exchange"]),
                    valid_from=date.fromisoformat(str(row["valid_from"])),
                    valid_to=date.fromisoformat(str(row["valid_to"])) if row["valid_to"] else None,
                    source=str(row["source"]),
                )
                for row in rows
            ]
            return tuple(histories)

    def get_instrument(self, instrument_id: InstrumentId) -> Instrument | None:
        with self._engine.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM instruments WHERE instrument_id = ?",
                (str(instrument_id.value),),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return Instrument(
                instrument_id=instrument_id,
                issuer_name=str(row["issuer_name"]),
                security_name=str(row["security_name"]),
                instrument_type=InstrumentType(str(row["instrument_type"])),
                exchange=str(row["exchange"]),
                currency=str(row["currency"]),
                active_from=date.fromisoformat(str(row["active_from"])),
                active_to=date.fromisoformat(str(row["active_to"])) if row["active_to"] else None,
                status=InstrumentStatus(str(row["status"])),
            )

    def upsert_identity(
        self,
        source_record: Instrument,
        symbol_histories: Sequence[SymbolHistory] = (),
    ) -> Instrument:
        with self._engine.transaction() as conn:
            cursor = conn.cursor()

            # First fetch existing symbol histories for the symbols involved to check overlap
            for h in symbol_histories:
                cursor.execute(
                    """
                    SELECT instrument_id, symbol, exchange, valid_from, valid_to, source
                    FROM instrument_symbol_history
                    WHERE symbol = ? AND exchange = ? AND instrument_id != ?
                    """,
                    (h.symbol.upper(), h.exchange.upper(), str(source_record.instrument_id.value)),
                )
                existing_rows = cursor.fetchall()
                existing_histories = [
                    SymbolHistory(
                        instrument_id=InstrumentId.from_uuid(UUID(str(r["instrument_id"]))),
                        symbol=str(r["symbol"]),
                        exchange=str(r["exchange"]),
                        valid_from=date.fromisoformat(str(r["valid_from"])),
                        valid_to=date.fromisoformat(str(r["valid_to"])) if r["valid_to"] else None,
                        source=str(r["source"]),
                    )
                    for r in existing_rows
                ]
                # Validate non-overlap with other instruments using the same ticker
                validate_non_overlapping_history([*existing_histories, h])

            # Also validate internal non-overlap within the passed histories
            validate_non_overlapping_history(symbol_histories)

            # Upsert instrument record
            cursor.execute(
                """
                INSERT INTO instruments (
                    instrument_id, issuer_name, security_name, instrument_type,
                    exchange, currency, active_from, active_to, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(instrument_id) DO UPDATE SET
                    issuer_name = excluded.issuer_name,
                    security_name = excluded.security_name,
                    instrument_type = excluded.instrument_type,
                    exchange = excluded.exchange,
                    currency = excluded.currency,
                    active_from = excluded.active_from,
                    active_to = excluded.active_to,
                    status = excluded.status
                """,
                (
                    str(source_record.instrument_id.value),
                    source_record.issuer_name,
                    source_record.security_name,
                    source_record.instrument_type.value,
                    source_record.exchange.upper(),
                    source_record.currency.upper(),
                    source_record.active_from.isoformat(),
                    source_record.active_to.isoformat() if source_record.active_to else None,
                    source_record.status.value,
                ),
            )

            # Insert new symbol history entries
            for h in symbol_histories:
                cursor.execute(
                    """
                    INSERT INTO instrument_symbol_history (
                        instrument_id, symbol, exchange, valid_from, valid_to, source
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(h.instrument_id.value),
                        h.symbol.upper(),
                        h.exchange.upper(),
                        h.valid_from.isoformat(),
                        h.valid_to.isoformat() if h.valid_to else None,
                        h.source,
                    ),
                )

            return source_record
