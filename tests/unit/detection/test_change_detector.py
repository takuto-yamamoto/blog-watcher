from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from tests.conftest import read_fixture
from tests.factories.detection import FetchResultFactory
from tests.factories.storage import BlogStateFactory

from blog_watcher.config.models import BlogConfig
from blog_watcher.detection.change_detector import ChangeDetector

if TYPE_CHECKING:
    from blog_watcher.detection.http_fetcher import FetchResult
    from blog_watcher.storage.models import BlogState


class FakeFetcher:
    def __init__(self, results: dict[str, FetchResult]) -> None:
        self._results = results

    async def fetch(self, url: str) -> FetchResult:
        return self._results[url]


class FakeBlogStateRepository:
    def __init__(self, initial: dict[str, BlogState] | None = None) -> None:
        self._states = dict(initial or {})

    def get(self, blog_id: str) -> BlogState | None:
        return self._states.get(blog_id)

    def upsert(self, state: BlogState) -> None:
        self._states[state.blog_id] = state


@pytest.fixture
def example_blog() -> BlogConfig:
    return BlogConfig(name="example", url="https://example.com")


@pytest.mark.unit
async def test_check_raises_when_fetch_result_missing_content(example_blog: BlogConfig) -> None:
    blog = example_blog
    blog_no_content = FetchResultFactory.build(content=None)

    fetcher = FakeFetcher({blog.url: blog_no_content})
    state_repo = FakeBlogStateRepository()
    detector = ChangeDetector(fetcher=fetcher, state_repo=state_repo)

    with pytest.raises(ValueError, match="content is None"):
        await detector.check(blog)


@pytest.mark.unit
async def test_check_raises_when_feed_result_missing_content(example_blog: BlogConfig) -> None:
    blog = example_blog
    blog_feed = FetchResultFactory.build(content=read_fixture("html/feed_link_rss.html"))
    feed_url = f"{blog.url}/feed.xml"
    feed_no_content = FetchResultFactory.build(content=None)

    fetcher = FakeFetcher({blog.url: blog_feed, feed_url: feed_no_content})
    state_repo = FakeBlogStateRepository()
    detector = ChangeDetector(fetcher=fetcher, state_repo=state_repo)

    with pytest.raises(ValueError, match="content is None"):
        await detector.check(blog)


@pytest.mark.unit
async def test_check_raises_when_feed_parse_fails(example_blog: BlogConfig) -> None:
    blog = example_blog
    blog_feed = FetchResultFactory.build(content=read_fixture("html/feed_link_rss.html"))
    feed_url = f"{blog.url}/feed.xml"
    feed_invalid = FetchResultFactory.build(content="<rss")

    fetcher = FakeFetcher({blog.url: blog_feed, feed_url: feed_invalid})
    state_repo = FakeBlogStateRepository()
    detector = ChangeDetector(fetcher=fetcher, state_repo=state_repo)

    with pytest.raises(ValueError, match="Failed to parse feed"):
        await detector.check(blog)


@pytest.mark.unit
async def test_check_uses_previous_state_recent_entry_keys(example_blog: BlogConfig) -> None:
    blog = example_blog
    blog_feed = FetchResultFactory.build(content=read_fixture("html/feed_link_rss.html"))
    feed_url = f"{blog.url}/feed.xml"
    feed_content = FetchResultFactory.build(content=read_fixture("feeds/rss_valid.xml"))
    current_entry_keys = json.dumps(["article-1-guid", "article-2-guid"])

    prev_entry_keys = current_entry_keys
    blog_prev_state = BlogStateFactory.build(blog_id=blog.blog_id, recent_entry_keys=prev_entry_keys)

    fetcher = FakeFetcher({blog.url: blog_feed, feed_url: feed_content})
    state_repo = FakeBlogStateRepository({blog.blog_id: blog_prev_state})
    detector = ChangeDetector(fetcher=fetcher, state_repo=state_repo)

    result = await detector.check(blog)

    assert result.changed is False
