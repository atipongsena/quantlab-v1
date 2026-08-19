from __future__ import annotations

import re
import sqlite3
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Protocol

from quantlab.common.errors import QuantLabError
from quantlab.infrastructure.partitions import (
    PartitionRef,
    read_partition,
    write_partition,
)


class AnalyticalQueryError(QuantLabError):
    """Raised when an analytical query fails or violates read-only semantics."""


FORBIDDEN_SQL_PATTERNS = (
    r"\bINSERT\b",
    r"\bUPDATE\b",
    r"\bDELETE\b",
    r"\bDROP\b",
    r"\bALTER\b",
    r"\bCREATE\b",
    r"\bREPLACE\b",
    r"\bTRUNCATE\b",
    r"\bATTACH\b",
    r"\bDETACH\b",
)


class AnalyticalStore(Protocol):
    def write_partition(
        self,
        dataset_id: str,
        table: str,
        partition_key: str,
        data: Sequence[Mapping[str, object]],
        schema: Mapping[str, str] | None = None,
    ) -> PartitionRef: ...

    def query(
        self,
        sql: str,
        refs: Sequence[PartitionRef],
        params: Sequence[object] | None = None,
    ) -> list[dict[str, object]]: ...


class LocalAnalyticalStore:
    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir.resolve()
        self._base_dir.mkdir(parents=True, exist_ok=True)

    @property
    def base_dir(self) -> Path:
        return self._base_dir

    def write_partition(
        self,
        dataset_id: str,
        table: str,
        partition_key: str,
        data: Sequence[Mapping[str, object]],
        schema: Mapping[str, str] | None = None,
    ) -> PartitionRef:
        return write_partition(
            base_dir=self._base_dir,
            dataset_id=dataset_id,
            table_name=table,
            partition_key=partition_key,
            rows=data,
            schema=schema,
        )

    def query(
        self,
        sql: str,
        refs: Sequence[PartitionRef],
        params: Sequence[object] | None = None,
    ) -> list[dict[str, object]]:
        self._assert_read_only(sql)

        # In-memory SQLite engine for deterministic offline analytical querying
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        try:
            # Group partitions by table name and load into temporary tables
            tables: dict[str, list[dict[str, object]]] = {}
            for ref in refs:
                rows = read_partition(ref)
                tables.setdefault(ref.table_name, []).extend(rows)

            for table_name, rows in tables.items():
                if not rows:
                    continue
                columns = list(rows[0].keys())
                col_defs = ", ".join(f'"{col}" TEXT' for col in columns)
                conn.execute(f'CREATE TEMP TABLE "{table_name}" ({col_defs})')

                placeholders = ", ".join("?" for _ in columns)
                insert_sql = f'INSERT INTO "{table_name}" VALUES ({placeholders})'
                conn.executemany(
                    insert_sql,
                    ([str(row.get(col, "")) for col in columns] for row in rows),
                )

            cursor = conn.cursor()
            if params is not None:
                cursor.execute(sql, list(params))
            else:
                cursor.execute(sql)
            results = [dict(row) for row in cursor.fetchall()]
            return results
        except sqlite3.Error as err:
            raise AnalyticalQueryError(f"Analytical query execution failed: {err}") from err
        finally:
            conn.close()

    def _assert_read_only(self, sql: str) -> None:
        upper_sql = sql.upper()
        for pattern in FORBIDDEN_SQL_PATTERNS:
            if re.search(pattern, upper_sql):
                raise AnalyticalQueryError(
                    f"Read-only analytical store rejected modifying SQL statement: {sql}"
                )
