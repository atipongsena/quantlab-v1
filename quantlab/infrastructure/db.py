from __future__ import annotations

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from quantlab.common.errors import QuantLabError


class DatabaseError(QuantLabError):
    """Raised when database operations fail."""


@dataclass(frozen=True, slots=True)
class DatabaseConfig:
    url: str = "sqlite:///:memory:"


class DatabaseEngine:
    def __init__(self, config: DatabaseConfig | None = None) -> None:
        self._config = config or DatabaseConfig()
        self._is_sqlite = self._config.url.startswith("sqlite")
        self._memory_conn: sqlite3.Connection | None = None
        if self._is_sqlite:
            path = self._config.url.removeprefix("sqlite:///").removeprefix("sqlite://")
            if path == ":memory:":
                self._memory_conn = sqlite3.connect(":memory:")
                self._memory_conn.row_factory = sqlite3.Row
                self._memory_conn.execute("PRAGMA foreign_keys = ON;")

    @property
    def is_sqlite(self) -> bool:
        return self._is_sqlite

    @property
    def url(self) -> str:
        return self._config.url

    def get_connection(self) -> sqlite3.Connection:
        if self._memory_conn is not None:
            return self._memory_conn
        if self._is_sqlite:
            path = self._config.url.removeprefix("sqlite:///").removeprefix("sqlite://")
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(path)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            return conn
        raise DatabaseError(f"Unsupported offline database url: {self._config.url}")

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            if self._memory_conn is None:
                conn.close()
