from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from tests.test_utils.fakes import FakeFetcher

if TYPE_CHECKING:
    from blog_watcher.config.models import BlogConfig
    from blog_watcher.detection.http_fetcher import FetchResult


@dataclass(frozen=True)
class BlogUrls:
    base: str
    feed: str
    robots: str
    sitemap: str
    sitemap_index: str


def blog_urls(blog: BlogConfig) -> BlogUrls:
    base = blog.url
    return BlogUrls(
        base=base,
        feed=f"{base}/feed.xml",
        robots=f"{base}/robots.txt",
        sitemap=f"{base}/sitemap.xml",
        sitemap_index=f"{base}/sitemap_index.xml",
    )


def build_feed_fetcher(
    blog: BlogConfig,
    *,
    html: FetchResult | None = None,
    feed: FetchResult | None = None,
) -> FakeFetcher:
    urls = blog_urls(blog)
    results: dict[str, FetchResult] = {}
    if html is not None:
        results[urls.base] = html
    if feed is not None:
        results[urls.feed] = feed
    return FakeFetcher(results)


def build_sitemap_fetcher(
    blog: BlogConfig,
    *,
    robots: FetchResult | None = None,
    sitemap: FetchResult | None = None,
    sitemap_index: FetchResult | None = None,
) -> FakeFetcher:
    urls = blog_urls(blog)
    results: dict[str, FetchResult] = {}
    if robots is not None:
        results[urls.robots] = robots
    if sitemap is not None:
        results[urls.sitemap] = sitemap
    if sitemap_index is not None:
        results[urls.sitemap_index] = sitemap_index
    return FakeFetcher(results)


def assert_not_fetched(fetcher: FakeFetcher, *needles: str) -> None:
    for needle in needles:
        assert not any(needle in url for url in fetcher.fetched_urls)
