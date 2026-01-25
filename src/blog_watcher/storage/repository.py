from __future__ import annotations

from datetime import datetime

import sqlite3

from .database import Database
from .models import BlogState, CheckHistory


class BlogStateRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def get(self, blog_id: str) -> BlogState | None:
        row = self._db.execute(
            "SELECT * FROM blog_state WHERE blog_id = ?", (blog_id,)
        ).fetchone()
        return self._row_to_state(row) if row else None

    def upsert(self, state: BlogState) -> None:
        self._db.execute(
            """
            INSERT INTO blog_state (
                blog_id,
                etag,
                last_modified,
                url_fingerprint,
                feed_url,
                sitemap_url,
                recent_entry_keys,
                last_checked_at,
                last_changed_at,
                consecutive_errors
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(blog_id) DO UPDATE SET
                etag=excluded.etag,
                last_modified=excluded.last_modified,
                url_fingerprint=excluded.url_fingerprint,
                feed_url=excluded.feed_url,
                sitemap_url=excluded.sitemap_url,
                recent_entry_keys=excluded.recent_entry_keys,
                last_checked_at=excluded.last_checked_at,
                last_changed_at=excluded.last_changed_at,
                consecutive_errors=excluded.consecutive_errors
            """,
            (
                state.blog_id,
                state.etag,
                state.last_modified,
                state.url_fingerprint,
                state.feed_url,
                state.sitemap_url,
                state.recent_entry_keys,
                state.last_checked_at.isoformat(),
                state.last_changed_at.isoformat() if state.last_changed_at else None,
                state.consecutive_errors,
            ),
        )

    def delete(self, blog_id: str) -> bool:
        cursor = self._db.execute(
            "DELETE FROM blog_state WHERE blog_id = ?", (blog_id,)
        )
        return cursor.rowcount > 0

    def list_all(self) -> list[BlogState]:
        rows = self._db.execute("SELECT * FROM blog_state").fetchall()
        return [self._row_to_state(row) for row in rows]

    def _row_to_state(self, row: sqlite3.Row) -> BlogState:
        return BlogState(
            blog_id=row["blog_id"],
            etag=row["etag"],
            last_modified=row["last_modified"],
            url_fingerprint=row["url_fingerprint"],
            feed_url=row["feed_url"],
            sitemap_url=row["sitemap_url"],
            recent_entry_keys=row["recent_entry_keys"],
            last_checked_at=datetime.fromisoformat(row["last_checked_at"]),
            last_changed_at=(
                datetime.fromisoformat(row["last_changed_at"])
                if row["last_changed_at"]
                else None
            ),
            consecutive_errors=row["consecutive_errors"],
        )


class CheckHistoryRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def add(self, entry: CheckHistory) -> None:
        self._db.execute(
            """
            INSERT INTO check_history (
                blog_id,
                checked_at,
                http_status,
                skipped,
                changed,
                url_fingerprint,
                error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry.blog_id,
                entry.checked_at.isoformat(),
                entry.http_status,
                1 if entry.skipped else 0,
                1 if entry.changed else 0,
                entry.url_fingerprint,
                entry.error_message,
            ),
        )

    def list_by_blog_id(self, blog_id: str) -> list[CheckHistory]:
        rows = self._db.execute(
            """
            SELECT blog_id, checked_at, http_status, skipped, changed,
                   url_fingerprint, error_message
            FROM check_history
            WHERE blog_id = ?
            ORDER BY checked_at DESC
            """,
            (blog_id,),
        ).fetchall()
        return [self._row_to_history(row) for row in rows]

    def _row_to_history(self, row: sqlite3.Row) -> CheckHistory:
        return CheckHistory(
            blog_id=row["blog_id"],
            checked_at=datetime.fromisoformat(row["checked_at"]),
            http_status=row["http_status"],
            skipped=bool(row["skipped"]),
            changed=bool(row["changed"]),
            url_fingerprint=row["url_fingerprint"],
            error_message=row["error_message"],
        )
