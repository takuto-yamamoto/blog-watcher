from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest
from tests.factories import BlogStateFactory, CheckHistoryFactory

from blog_watcher.storage import BlogStateRepository, CheckHistoryRepository, Database

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path


@pytest.fixture
def database(tmp_path: Path) -> Generator[Database, None, None]:
    db_path = tmp_path / "test.db"
    db = Database(db_path)
    db.initialize()
    yield db
    db.close()


def test_upsert_and_get_round_trip(database: Database) -> None:
    repo = BlogStateRepository(database)
    state = BlogStateFactory.build(blog_id="blog-1")

    repo.upsert(state)
    fetched = repo.get("blog-1")

    assert fetched == state


def test_get_nonexistent_returns_none(database: Database) -> None:
    repo = BlogStateRepository(database)

    assert repo.get("missing") is None


def test_upsert_updates_existing_record(database: Database) -> None:
    repo = BlogStateRepository(database)
    first = BlogStateFactory.build(blog_id="blog-1", etag="etag-1")
    second = BlogStateFactory.build(blog_id="blog-1", etag="etag-2")

    repo.upsert(first)
    repo.upsert(second)

    fetched = repo.get("blog-1")

    assert fetched == second


def test_history_query_orders_by_timestamp(database: Database) -> None:
    history_repo = CheckHistoryRepository(database)
    older = CheckHistoryFactory.build(
        blog_id="blog-1",
        checked_at=datetime(2024, 1, 1, tzinfo=UTC),
    )
    newer = CheckHistoryFactory.build(
        blog_id="blog-1",
        checked_at=datetime(2024, 1, 2, tzinfo=UTC),
    )

    history_repo.add(older)
    history_repo.add(newer)

    results = history_repo.list_by_blog_id("blog-1")

    assert results == [newer, older]


def test_delete_existing_returns_true(database: Database) -> None:
    repo = BlogStateRepository(database)
    state = BlogStateFactory.build(blog_id="blog-1")

    repo.upsert(state)

    assert repo.delete("blog-1") is True
    assert repo.get("blog-1") is None


def test_delete_nonexistent_returns_false(database: Database) -> None:
    repo = BlogStateRepository(database)

    assert repo.delete("missing") is False


def test_list_all_returns_all_states(database: Database) -> None:
    repo = BlogStateRepository(database)
    state_a = BlogStateFactory.build(blog_id="blog-a")
    state_b = BlogStateFactory.build(blog_id="blog-b")

    repo.upsert(state_a)
    repo.upsert(state_b)

    results = repo.list_all()

    assert {state.blog_id for state in results} == {"blog-a", "blog-b"}


# NOTE: concurrent read behavior is deferred until DB connection strategy is decided.
