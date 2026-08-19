from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Protocol

from quantlab.domain.identity import (
    InstrumentId,
    _require_nonempty,
    require_date_only,
    require_decimal,
    require_timezone_aware,
)
from quantlab.infrastructure.db import DatabaseEngine


@dataclass(frozen=True, slots=True)
class FundamentalValue:
    instrument_id: InstrumentId
    period_end: date
    filing_date: date
    available_at: datetime
    metric: str
    value: Decimal
    is_restatement: bool
    source: str

    def __post_init__(self) -> None:
        if not isinstance(self.instrument_id, InstrumentId):
            raise TypeError("instrument_id must be an InstrumentId")
        require_date_only(self.period_end, "period_end")
        require_date_only(self.filing_date, "filing_date")
        require_timezone_aware(self.available_at, "available_at")
        _require_nonempty(self.metric, "metric")
        require_decimal(self.value, "value")
        if not isinstance(self.is_restatement, bool):
            raise TypeError("is_restatement must be a boolean")
        _require_nonempty(self.source, "source")


class FundamentalStore(Protocol):
    def record_statement(self, statement: FundamentalValue) -> None: ...

    def record_statements(self, statements: Sequence[FundamentalValue]) -> None: ...

    def as_of(
        self,
        instrument_id: InstrumentId,
        as_of: datetime,
        metric: str,
        period_end: date | None = None,
    ) -> FundamentalValue | None: ...

    def restatement_history(
        self,
        instrument_id: InstrumentId,
        period_end: date,
        metric: str,
    ) -> tuple[FundamentalValue, ...]: ...


class SqlFundamentalStore(FundamentalStore):
    def __init__(self, engine: DatabaseEngine) -> None:
        self._engine = engine

    def record_statement(self, statement: FundamentalValue) -> None:
        self.record_statements([statement])

    def record_statements(self, statements: Sequence[FundamentalValue]) -> None:
        if not statements:
            return
        with self._engine.transaction() as conn:
            cursor = conn.cursor()
            for s in statements:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO fundamentals (
                        instrument_id, period_end, filing_date, available_at,
                        metric, value, is_restatement, source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(s.instrument_id.value),
                        s.period_end.isoformat(),
                        s.filing_date.isoformat(),
                        s.available_at.isoformat(),
                        s.metric.lower(),
                        str(s.value),
                        1 if s.is_restatement else 0,
                        s.source,
                    ),
                )

    def as_of(
        self,
        instrument_id: InstrumentId,
        as_of: datetime,
        metric: str,
        period_end: date | None = None,
    ) -> FundamentalValue | None:
        inst_str = str(instrument_id.value)
        as_of_iso = as_of.isoformat()
        metric_norm = metric.lower()

        query = """
        SELECT
            instrument_id, period_end, filing_date, available_at,
            metric, value, is_restatement, source
        FROM fundamentals
        WHERE instrument_id = ?
          AND metric = ?
          AND available_at <= ?
        """
        params: list[object] = [inst_str, metric_norm, as_of_iso]

        if period_end is not None:
            query += " AND period_end = ?"
            params.append(period_end.isoformat())
            # For a specific period end, order by latest available_at first
            query += " ORDER BY available_at DESC, id DESC LIMIT 1"
        else:
            # For general latest available, order by latest period_end then latest available_at
            query += " ORDER BY period_end DESC, available_at DESC, id DESC LIMIT 1"

        with self._engine.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            if row is None:
                return None
            return FundamentalValue(
                instrument_id=instrument_id,
                period_end=date.fromisoformat(str(row["period_end"])),
                filing_date=date.fromisoformat(str(row["filing_date"])),
                available_at=datetime.fromisoformat(str(row["available_at"])).replace(tzinfo=UTC),
                metric=str(row["metric"]),
                value=Decimal(str(row["value"])),
                is_restatement=bool(row["is_restatement"]),
                source=str(row["source"]),
            )

    def restatement_history(
        self,
        instrument_id: InstrumentId,
        period_end: date,
        metric: str,
    ) -> tuple[FundamentalValue, ...]:
        inst_str = str(instrument_id.value)
        period_end_str = period_end.isoformat()
        metric_norm = metric.lower()

        query = """
        SELECT
            instrument_id, period_end, filing_date, available_at,
            metric, value, is_restatement, source
        FROM fundamentals
        WHERE instrument_id = ?
          AND period_end = ?
          AND metric = ?
        ORDER BY available_at ASC, id ASC
        """
        with self._engine.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (inst_str, period_end_str, metric_norm))
            rows = cursor.fetchall()
            return tuple(
                FundamentalValue(
                    instrument_id=instrument_id,
                    period_end=date.fromisoformat(str(row["period_end"])),
                    filing_date=date.fromisoformat(str(row["filing_date"])),
                    available_at=datetime.fromisoformat(str(row["available_at"])).replace(
                        tzinfo=UTC
                    ),
                    metric=str(row["metric"]),
                    value=Decimal(str(row["value"])),
                    is_restatement=bool(row["is_restatement"]),
                    source=str(row["source"]),
                )
                for row in rows
            )
