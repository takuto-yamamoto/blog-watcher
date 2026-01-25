from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

import pytest

from blog_watcher.storage import (
    BlogState,
    BlogStateRepository,
    CheckHistory,
    CheckHistoryRepository,
    Database,
)


def _now_iso() -> datetime:
    return datetime.now(timezone.utc)


@pytest.fixture()
def database(tmp_path: Path) -> Generator[Database, None, None]:
    db_path = tmp_path / "test.db"
    db = Database(db_path)
    db.initialize()
    yield db
    db.close()


def test_upsert_and_get_round_trip(database: Database) -> None:
    repo = BlogStateRepository(database)
    state = BlogState(
        blog_id="blog-1",
        etag="etag-1",
        last_modified="last-mod-1",
        url_fingerprint="hash-1",
        feed_url=None,
        sitemap_url=None,
        recent_entry_keys=None,
        last_checked_at=_now_iso(),
        last_changed_at=None,
        consecutive_errors=0,
    )

    repo.upsert(state)
    fetched = repo.get("blog-1")

    assert fetched == state


def test_get_nonexistent_returns_none(database: Database) -> None:
    repo = BlogStateRepository(database)

    assert repo.get("missing") is None


def test_upsert_updates_existing_record(database: Database) -> None:
    repo = BlogStateRepository(database)
    first = BlogState(
        blog_id="blog-1",
        etag="etag-1",
        last_modified="last-mod-1",
        url_fingerprint="hash-1",
        feed_url=None,
        sitemap_url=None,
        recent_entry_keys=None,
        last_checked_at=_now_iso(),
        last_changed_at=None,
        consecutive_errors=0,
    )
    second = BlogState(
        blog_id="blog-1",
        etag="etag-2",
        last_modified="last-mod-2",
        url_fingerprint="hash-2",
        feed_url="https://example.com/feed.xml",
        sitemap_url="https://example.com/sitemap.xml",
        recent_entry_keys='["k1","k2"]',
        last_checked_at=_now_iso(),
        last_changed_at=_now_iso(),
        consecutive_errors=1,
    )

    repo.upsert(first)
    repo.upsert(second)

    fetched = repo.get("blog-1")

    assert fetched == second


def test_history_query_orders_by_timestamp(database: Database) -> None:
    history_repo = CheckHistoryRepository(database)
    older = CheckHistory(
        blog_id="blog-1",
        checked_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        http_status=200,
        skipped=False,
        changed=False,
        url_fingerprint="hash-1",
        error_message=None,
    )
    newer = CheckHistory(
        blog_id="blog-1",
        checked_at=datetime(2024, 1, 2, tzinfo=timezone.utc),
        http_status=304,
        skipped=True,
        changed=False,
        url_fingerprint=None,
        error_message=None,
    )

    history_repo.add(older)
    history_repo.add(newer)

    results = history_repo.list_by_blog_id("blog-1")

    assert results == [newer, older]


def test_delete_existing_returns_true(database: Database) -> None:
    repo = BlogStateRepository(database)
    state = BlogState(
        blog_id="blog-1",
        etag=None,
        last_modified=None,
        url_fingerprint=None,
        feed_url=None,
        sitemap_url=None,
        recent_entry_keys=None,
        last_checked_at=_now_iso(),
        last_changed_at=None,
        consecutive_errors=0,
    )

    repo.upsert(state)

    assert repo.delete("blog-1") is True
    assert repo.get("blog-1") is None


def test_delete_nonexistent_returns_false(database: Database) -> None:
    repo = BlogStateRepository(database)

    assert repo.delete("missing") is False


def test_list_all_returns_all_states(database: Database) -> None:
    repo = BlogStateRepository(database)
    state_a = BlogState(
        blog_id="blog-a",
        etag=None,
        last_modified=None,
        url_fingerprint=None,
        feed_url=None,
        sitemap_url=None,
        recent_entry_keys=None,
        last_checked_at=_now_iso(),
        last_changed_at=None,
        consecutive_errors=0,
    )
    state_b = BlogState(
        blog_id="blog-b",
        etag="etag",
        last_modified="last-mod",
        url_fingerprint="hash",
        feed_url="https://example.com/feed.xml",
        sitemap_url=None,
        recent_entry_keys=None,
        last_checked_at=_now_iso(),
        last_changed_at=None,
        consecutive_errors=0,
    )

    repo.upsert(state_a)
    repo.upsert(state_b)

    results = repo.list_all()

    assert {state.blog_id for state in results} == {"blog-a", "blog-b"}


# NOTE: concurrent read behavior is deferred until DB connection strategy is decided.
