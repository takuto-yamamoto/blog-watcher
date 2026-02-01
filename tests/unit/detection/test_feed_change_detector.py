from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from tests.test_utils.factories import BlogStateFactory, FetchResultFactory
from tests.test_utils.helpers import build_feed_fetcher

from blog_watcher.config.models import BlogConfig
from blog_watcher.detection.feed import FeedChangeDetector

if TYPE_CHECKING:
    from blog_watcher.detection.http_fetcher import FetchResult


@pytest.fixture
def blog() -> BlogConfig:
    return BlogConfig(name="example", url="https://example.com")


@pytest.mark.unit
async def test_feed_change_detector_returns_ok_when_feed_parses(
    blog: BlogConfig,
    feed_link_html: FetchResult,
    rss_valid: FetchResult,
) -> None:
    fetcher = build_feed_fetcher(blog, html=feed_link_html, feed=rss_valid)
    detector = FeedChangeDetector(fetcher=fetcher)

    result = await detector.detect(feed_link_html, blog.url, None)

    assert result.ok is True
    assert result.feed_url == f"{blog.url}/feed.xml"
    assert result.changed is False


@pytest.mark.unit
async def test_feed_change_detector_detects_change_vs_previous_entry_keys(
    blog: BlogConfig,
    feed_link_html: FetchResult,
    rss_valid: FetchResult,
) -> None:
    fetcher = build_feed_fetcher(blog, html=feed_link_html, feed=rss_valid)
    previous_state = BlogStateFactory.build(blog_id=blog.blog_id, recent_entry_keys=json.dumps(["old-entry-1", "old-entry-2"]))
    detector = FeedChangeDetector(fetcher=fetcher)

    result = await detector.detect(feed_link_html, blog.url, previous_state)

    assert result.changed is True


@pytest.mark.unit
async def test_feed_change_detector_returns_not_ok_when_no_feed_links(blog: BlogConfig) -> None:
    html = FetchResultFactory.build(content="<html><body>no feed</body></html>")
    fetcher = build_feed_fetcher(blog, html=html)
    detector = FeedChangeDetector(fetcher=fetcher)

    result = await detector.detect(html, blog.url, None)

    assert result.ok is False
    assert result.feed_url is None
    assert result.changed is False
