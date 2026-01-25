from __future__ import annotations

import sqlite3
from datetime import datetime

from .database import Database
from .models import BlogState, CheckHistory
from .sql import (
    BLOG_STATE_DELETE_SQL,
    BLOG_STATE_GET_SQL,
    BLOG_STATE_LIST_ALL_SQL,
    BLOG_STATE_UPSERT_SQL,
    CHECK_HISTORY_ADD_SQL,
    CHECK_HISTORY_LIST_BY_BLOG_ID_SQL,
)


class BlogStateRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def get(self, blog_id: str) -> BlogState | None:
        row = self._db.execute(BLOG_STATE_GET_SQL, (blog_id,)).fetchone()
        return self._row_to_state(row) if row else None

    def upsert(self, state: BlogState) -> None:
        self._db.execute(
            BLOG_STATE_UPSERT_SQL,
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
        cursor = self._db.execute(BLOG_STATE_DELETE_SQL, (blog_id,))
        return cursor.rowcount > 0

    def list_all(self) -> list[BlogState]:
        rows = self._db.execute(BLOG_STATE_LIST_ALL_SQL).fetchall()
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
            CHECK_HISTORY_ADD_SQL,
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
            CHECK_HISTORY_LIST_BY_BLOG_ID_SQL,
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
