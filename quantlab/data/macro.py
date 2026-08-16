from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Protocol

from quantlab.domain.identity import (
    _require_nonempty,
    require_date_only,
    require_decimal,
    require_timezone_aware,
)
from quantlab.infrastructure.db import DatabaseEngine


@dataclass(frozen=True, slots=True)
class MacroVintage:
    series_id: str
    period_date: date
    release_time: datetime
    value: Decimal
    source: str

    def __post_init__(self) -> None:
        _require_nonempty(self.series_id, "series_id")
        require_date_only(self.period_date, "period_date")
        require_timezone_aware(self.release_time, "release_time")
        require_decimal(self.value, "value")
        _require_nonempty(self.source, "source")


class MacroStore(Protocol):
    def record_vintage(self, vintage: MacroVintage) -> None: ...

    def record_vintages(self, vintages: Sequence[MacroVintage]) -> None: ...

    def as_of(
        self,
        series_id: str,
        as_of: datetime,
        period_date: date | None = None,
    ) -> MacroVintage | None: ...

    def vintages_for_period(
        self,
        series_id: str,
        period_date: date,
    ) -> tuple[MacroVintage, ...]: ...


class SqlMacroStore(MacroStore):
    def __init__(self, engine: DatabaseEngine) -> None:
        self._engine = engine

    def record_vintage(self, vintage: MacroVintage) -> None:
        self.record_vintages([vintage])

    def record_vintages(self, vintages: Sequence[MacroVintage]) -> None:
        if not vintages:
            return
        with self._engine.transaction() as conn:
            cursor = conn.cursor()
            for v in vintages:
                cursor.execute(
                    """
                    INSERT INTO macro_vintages (
                        series_id, period_date, release_time, value, source
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        v.series_id.upper(),
                        v.period_date.isoformat(),
                        v.release_time.isoformat(),
                        str(v.value),
                        v.source,
                    ),
                )

    def as_of(
        self,
        series_id: str,
        as_of: datetime,
        period_date: date | None = None,
    ) -> MacroVintage | None:
        series_norm = series_id.upper()
        as_of_iso = as_of.isoformat()

        query = """
        SELECT series_id, period_date, release_time, value, source
        FROM macro_vintages
        WHERE series_id = ?
          AND release_time <= ?
        """
        params: list[object] = [series_norm, as_of_iso]

        if period_date is not None:
            query += " AND period_date = ?"
            params.append(period_date.isoformat())
            query += " ORDER BY release_time DESC, id DESC LIMIT 1"
        else:
            query += " ORDER BY period_date DESC, release_time DESC, id DESC LIMIT 1"

        with self._engine.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            if row is None:
                return None
            return MacroVintage(
                series_id=str(row["series_id"]),
                period_date=date.fromisoformat(str(row["period_date"])),
                release_time=datetime.fromisoformat(str(row["release_time"])).replace(tzinfo=UTC),
                value=Decimal(str(row["value"])),
                source=str(row["source"]),
            )

    def vintages_for_period(
        self,
        series_id: str,
        period_date: date,
    ) -> tuple[MacroVintage, ...]:
        series_norm = series_id.upper()
        period_date_str = period_date.isoformat()

        query = """
        SELECT series_id, period_date, release_time, value, source
        FROM macro_vintages
        WHERE series_id = ?
          AND period_date = ?
        ORDER BY release_time ASC, id ASC
        """
        with self._engine.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (series_norm, period_date_str))
            rows = cursor.fetchall()
            return tuple(
                MacroVintage(
                    series_id=str(row["series_id"]),
                    period_date=date.fromisoformat(str(row["period_date"])),
                    release_time=datetime.fromisoformat(str(row["release_time"])).replace(
                        tzinfo=UTC
                    ),
                    value=Decimal(str(row["value"])),
                    source=str(row["source"]),
                )
                for row in rows
            )
