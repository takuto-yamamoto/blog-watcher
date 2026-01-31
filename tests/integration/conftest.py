from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest

from blog_watcher.detection.change_detector import ChangeDetector
from blog_watcher.detection.http_fetcher import HttpFetcher
from blog_watcher.storage import BlogStateRepository, Database

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Generator
    from pathlib import Path

    from pytest_httpserver import HTTPServer


@pytest.fixture
def database(tmp_path: Path) -> Generator[Database, None, None]:
    db_path = tmp_path / "test.db"
    db = Database(db_path)
    db.initialize()
    yield db
    db.close()


@pytest.fixture
def state_repo(database: Database) -> BlogStateRepository:
    return BlogStateRepository(database)


@pytest.fixture
async def fetcher(httpserver: HTTPServer) -> AsyncIterator[HttpFetcher]:
    async with httpx.AsyncClient(base_url=httpserver.url_for("/")) as client:
        yield HttpFetcher(client)


@pytest.fixture
def detector(fetcher: HttpFetcher, state_repo: BlogStateRepository) -> ChangeDetector:
    return ChangeDetector(fetcher=fetcher, state_repo=state_repo)
