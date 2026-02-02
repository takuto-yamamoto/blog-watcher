from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from blog_watcher.config.models import BlogConfig
from blog_watcher.detection.models import DetectorConfig
from blog_watcher.detection.sitemap import SitemapChangeDetector
from tests.test_utils.factories import BlogStateFactory, FetchResultFactory
from tests.test_utils.fakes import FakeFetcher
from tests.test_utils.helpers import assert_not_fetched, blog_urls, build_sitemap_fetcher

if TYPE_CHECKING:
    from blog_watcher.detection.http_fetcher import FetchResult


def _build_sitemap_urlset(urls: list[str]) -> str:
    entries = "".join(f"<url><loc>{url}</loc></url>" for url in urls)
    return f'<?xml version="1.0" encoding="UTF-8"?><urlset>{entries}</urlset>'


async def test_sitemap_change_detector_returns_ok_when_sitemap_parses(robots_allow_all: FetchResult) -> None:
    blog = BlogConfig(name="example", url="https://example.com")
    urls = ["https://example.com/posts/a", "https://example.com/posts/b"]
    sitemap = FetchResultFactory.build(content=_build_sitemap_urlset(urls))

    fetcher = build_sitemap_fetcher(blog, robots=robots_allow_all, sitemap=sitemap)
    detector = SitemapChangeDetector(fetcher=fetcher, config=DetectorConfig())

    result = await detector.detect(blog.url, previous_state=None)

    assert result.ok is True
    assert result.sitemap_url == f"{blog.url}/sitemap.xml"
    assert result.changed is False


async def test_sitemap_change_detector_detects_change_when_fingerprint_differs(robots_allow_all: FetchResult) -> None:
    blog = BlogConfig(name="example", url="https://example.com")
    urls = ["https://example.com/posts/a", "https://example.com/posts/b"]
    sitemap = FetchResultFactory.build(content=_build_sitemap_urlset(urls))
    previous_state = BlogStateFactory.build(blog_id=blog.blog_id, url_fingerprint="old-fingerprint")

    fetcher = build_sitemap_fetcher(blog, robots=robots_allow_all, sitemap=sitemap)
    detector = SitemapChangeDetector(fetcher=fetcher, config=DetectorConfig())

    result = await detector.detect(blog.url, previous_state)

    assert result.changed is True


async def test_sitemap_change_detector_returns_not_ok_on_invalid_sitemap(robots_allow_all: FetchResult) -> None:
    blog = BlogConfig(name="example", url="https://example.com")
    sitemap = FetchResultFactory.build(content="<not-a-sitemap/>")

    fetcher = build_sitemap_fetcher(blog, robots=robots_allow_all, sitemap=sitemap)
    detector = SitemapChangeDetector(fetcher=fetcher, config=DetectorConfig())

    result = await detector.detect(blog.url, previous_state=None)

    assert result.ok is False
    assert result.sitemap_url is None
    assert result.fingerprint is None
    assert result.changed is False


async def test_sitemap_uses_cached_url_when_fresh() -> None:
    blog = BlogConfig(name="example", url="https://example.com")
    urls_info = blog_urls(blog)
    sitemap_xml = _build_sitemap_urlset(["https://example.com/posts/a"])
    sitemap = FetchResultFactory.build(content=sitemap_xml)

    fetcher = FakeFetcher({urls_info.sitemap: sitemap})
    previous_state = BlogStateFactory.build(
        blog_id=blog.blog_id,
        sitemap_url=urls_info.sitemap,
        last_checked_at=datetime.now(UTC) - timedelta(days=1),
    )
    detector = SitemapChangeDetector(fetcher=fetcher, config=DetectorConfig())

    result = await detector.detect(blog.url, previous_state)

    assert result.ok is True
    assert result.sitemap_url == urls_info.sitemap
    assert_not_fetched(fetcher, "robots.txt")


async def test_sitemap_rediscovers_when_cache_stale(robots_allow_all: FetchResult) -> None:
    blog = BlogConfig(name="example", url="https://example.com")
    urls_info = blog_urls(blog)
    sitemap_xml = _build_sitemap_urlset(["https://example.com/posts/a"])
    sitemap = FetchResultFactory.build(content=sitemap_xml)

    fetcher = FakeFetcher({urls_info.robots: robots_allow_all, urls_info.sitemap: sitemap})
    previous_state = BlogStateFactory.build(
        blog_id=blog.blog_id,
        sitemap_url=urls_info.sitemap,
        last_checked_at=datetime.now(UTC) - timedelta(days=30),
    )
    detector = SitemapChangeDetector(fetcher=fetcher, config=DetectorConfig(cache_ttl_days=7))

    result = await detector.detect(blog.url, previous_state)

    assert result.ok is True


async def test_sitemap_rediscovers_when_cached_url_fails(robots_allow_all: FetchResult) -> None:
    blog = BlogConfig(name="example", url="https://example.com")
    urls_info = blog_urls(blog)
    sitemap_xml = _build_sitemap_urlset(["https://example.com/posts/a"])
    sitemap = FetchResultFactory.build(content=sitemap_xml)

    # Cached URL is different and not in fetcher → fails → fallback to robots discovery
    fetcher = FakeFetcher({urls_info.robots: robots_allow_all, urls_info.sitemap: sitemap})
    previous_state = BlogStateFactory.build(
        blog_id=blog.blog_id,
        sitemap_url="https://example.com/old-sitemap.xml",
        last_checked_at=datetime.now(UTC) - timedelta(days=1),
    )
    detector = SitemapChangeDetector(fetcher=fetcher, config=DetectorConfig())

    result = await detector.detect(blog.url, previous_state)

    assert result.ok is True
    assert result.sitemap_url == urls_info.sitemap
