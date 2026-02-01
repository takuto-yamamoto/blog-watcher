from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from tests.test_utils.factories import BlogStateFactory, FetchResultFactory
from tests.test_utils.helpers import build_sitemap_fetcher

from blog_watcher.config.models import BlogConfig
from blog_watcher.detection.models import DetectorConfig
from blog_watcher.detection.sitemap import SitemapChangeDetector

if TYPE_CHECKING:
    from blog_watcher.detection.http_fetcher import FetchResult


def _build_sitemap_urlset(urls: list[str]) -> str:
    entries = "".join(f"<url><loc>{url}</loc></url>" for url in urls)
    return f'<?xml version="1.0" encoding="UTF-8"?><urlset>{entries}</urlset>'


@pytest.mark.unit
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


@pytest.mark.unit
async def test_sitemap_change_detector_detects_change_when_fingerprint_differs(robots_allow_all: FetchResult) -> None:
    blog = BlogConfig(name="example", url="https://example.com")
    urls = ["https://example.com/posts/a", "https://example.com/posts/b"]
    sitemap = FetchResultFactory.build(content=_build_sitemap_urlset(urls))
    previous_state = BlogStateFactory.build(blog_id=blog.blog_id, url_fingerprint="old-fingerprint")

    fetcher = build_sitemap_fetcher(blog, robots=robots_allow_all, sitemap=sitemap)
    detector = SitemapChangeDetector(fetcher=fetcher, config=DetectorConfig())

    result = await detector.detect(blog.url, previous_state)

    assert result.changed is True


@pytest.mark.unit
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
