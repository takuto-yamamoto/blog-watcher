from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class BlogStateRow:
    blog_id: str
    last_checked_at: str | None
    url_fingerprint: str | None
    feed_url: str | None
    recent_entry_keys: str | None
    last_changed_at: str | None
    consecutive_errors: int


def list_blog_states(db_path: Path) -> list[BlogStateRow]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT * FROM blog_state").fetchall()
        return [
            BlogStateRow(
                blog_id=r["blog_id"],
                last_checked_at=r["last_checked_at"],
                url_fingerprint=r["url_fingerprint"],
                feed_url=r["feed_url"],
                recent_entry_keys=r["recent_entry_keys"],
                last_changed_at=r["last_changed_at"],
                consecutive_errors=r["consecutive_errors"],
            )
            for r in rows
        ]
    finally:
        conn.close()
