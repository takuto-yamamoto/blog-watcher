from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from blog_watcher.config.models import BlogConfig
from blog_watcher.detection.feed import FeedChangeDetector
from blog_watcher.detection.models import DetectorConfig
from tests.test_utils.factories import BlogStateFactory, FetchResultFactory
from tests.test_utils.fakes import FakeFetcher
from tests.test_utils.helpers import assert_not_fetched, blog_urls, build_feed_fetcher

if TYPE_CHECKING:
    from blog_watcher.detection.http_fetcher import FetchResult


@pytest.fixture
def blog() -> BlogConfig:
    return BlogConfig(name="example", url="https://example.com")


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


async def test_feed_change_detector_returns_not_ok_when_no_feed_links(blog: BlogConfig) -> None:
    html = FetchResultFactory.build(content="<html><body>no feed</body></html>")
    fetcher = build_feed_fetcher(blog, html=html)
    detector = FeedChangeDetector(fetcher=fetcher)

    result = await detector.detect(html, blog.url, None)

    assert result.ok is False
    assert result.feed_url is None
    assert result.changed is False


async def test_feed_uses_cached_url_when_fresh(
    blog: BlogConfig,
    rss_valid: FetchResult,
) -> None:
    urls = blog_urls(blog)
    fetcher = FakeFetcher({urls.feed: rss_valid})
    previous_state = BlogStateFactory.build(
        blog_id=blog.blog_id,
        feed_url=urls.feed,
        last_checked_at=datetime.now(UTC) - timedelta(days=1),
    )
    detector = FeedChangeDetector(fetcher=fetcher, config=DetectorConfig())

    result = await detector.detect(FetchResultFactory.build(), blog.url, previous_state)

    assert result.ok is True
    assert result.feed_url == urls.feed
    assert_not_fetched(fetcher, "example.com/feed_link")


async def test_feed_rediscovers_when_cache_stale(
    blog: BlogConfig,
    feed_link_html: FetchResult,
    rss_valid: FetchResult,
) -> None:
    urls = blog_urls(blog)
    fetcher = FakeFetcher({urls.base: feed_link_html, urls.feed: rss_valid})
    previous_state = BlogStateFactory.build(
        blog_id=blog.blog_id,
        feed_url=urls.feed,
        last_checked_at=datetime.now(UTC) - timedelta(days=30),
    )
    detector = FeedChangeDetector(fetcher=fetcher, config=DetectorConfig(cache_ttl_days=7))

    result = await detector.detect(feed_link_html, blog.url, previous_state)

    assert result.ok is True
    assert result.feed_url == urls.feed


async def test_feed_rediscovers_when_cached_url_fails(
    blog: BlogConfig,
    feed_link_html: FetchResult,
    rss_valid: FetchResult,
) -> None:
    urls = blog_urls(blog)
    # Cached URL not in fetcher results → returns None content → fallback
    fetcher = FakeFetcher({urls.feed: rss_valid})
    cached_url = "https://example.com/old-feed.xml"
    previous_state = BlogStateFactory.build(
        blog_id=blog.blog_id,
        feed_url=cached_url,
        last_checked_at=datetime.now(UTC) - timedelta(days=1),
    )
    detector = FeedChangeDetector(fetcher=fetcher, config=DetectorConfig())

    result = await detector.detect(feed_link_html, blog.url, previous_state)

    assert result.ok is True
    assert result.feed_url == urls.feed
