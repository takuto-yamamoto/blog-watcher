from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

from .sql import SCHEMA_SQL

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path


class Database:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._connection: sqlite3.Connection | None = None

    def connect(self) -> sqlite3.Connection:
        if self._connection is None:
            self._connection = sqlite3.connect(self._path)
            self._connection.row_factory = sqlite3.Row
        return self._connection

    def initialize(self) -> None:
        connection = self.connect()
        connection.executescript(SCHEMA_SQL)
        connection.commit()

    def execute(
        self,
        query: str,
        params: Sequence[object] | None = None,
    ) -> sqlite3.Cursor:
        connection = self.connect()
        cursor = connection.execute(query, params or ())
        connection.commit()
        return cursor

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None
