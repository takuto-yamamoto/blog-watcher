from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from blog_watcher.config.models import BlogConfig
from tests.test_utils.helpers import read_fixture

if TYPE_CHECKING:
    from pytest_httpserver import HTTPServer

    from blog_watcher.detection.change_detector import ChangeDetector
    from blog_watcher.storage import BlogStateRepository

pytestmark = [pytest.mark.integration]


@pytest.mark.slow
async def test_second_check_with_same_entries_reports_no_change(
    detector: ChangeDetector,
    httpserver: HTTPServer,
) -> None:
    html_content = read_fixture("html/feed_link_rss.html")
    feed_content = read_fixture("feeds/rss_valid.xml")

    httpserver.expect_request("/").respond_with_data(
        html_content,
        status=200,
        headers={"Content-Type": "text/html; charset=utf-8"},
    )
    httpserver.expect_request("/feed.xml").respond_with_data(
        feed_content,
        status=200,
        headers={"Content-Type": "application/rss+xml"},
    )

    blog = BlogConfig(name="example", url=httpserver.url_for("/"))
    first = await detector.check(blog)
    second = await detector.check(blog)

    assert first.changed is True
    assert second.changed is False


@pytest.mark.slow
async def test_second_check_with_new_entries_reports_change(
    detector: ChangeDetector,
    httpserver: HTTPServer,
) -> None:
    html_content = read_fixture("html/feed_link_rss.html")
    feed_content = read_fixture("feeds/rss_valid.xml")

    httpserver.expect_request("/").respond_with_data(
        html_content,
        status=200,
        headers={"Content-Type": "text/html; charset=utf-8"},
    )
    httpserver.expect_request("/feed.xml").respond_with_data(
        feed_content,
        status=200,
        headers={"Content-Type": "application/rss+xml"},
    )

    blog = BlogConfig(name="example", url=httpserver.url_for("/"))
    first = await detector.check(blog)

    updated_feed = read_fixture("feeds/rss_valid_updated.xml")
    httpserver.clear()  # type: ignore[no-untyped-call]
    httpserver.expect_request("/").respond_with_data(
        html_content,
        status=200,
        headers={"Content-Type": "text/html; charset=utf-8"},
    )
    httpserver.expect_request("/feed.xml").respond_with_data(
        updated_feed,
        status=200,
        headers={"Content-Type": "application/rss+xml"},
    )

    second = await detector.check(blog)

    assert first.changed is True
    assert second.changed is True


async def test_first_check_without_feed_or_sitemap_is_changed(
    detector: ChangeDetector,
    httpserver: HTTPServer,
) -> None:
    html_content = "<html><body>no feed</body></html>"
    robots_txt = "User-agent: *\nDisallow:"

    httpserver.expect_request("/").respond_with_data(
        html_content,
        status=200,
        headers={"Content-Type": "text/html; charset=utf-8"},
    )
    httpserver.expect_request("/robots.txt").respond_with_data(
        robots_txt,
        status=200,
        headers={"Content-Type": "text/plain; charset=utf-8"},
    )
    for path in ("/feed", "/rss.xml", "/atom.xml", "/rss", "/feed.xml"):
        httpserver.expect_request(path).respond_with_data("not a feed", status=404)
    httpserver.expect_request("/sitemap.xml").respond_with_data("not a sitemap", status=404)
    httpserver.expect_request("/sitemap_index.xml").respond_with_data("not a sitemap", status=404)

    blog = BlogConfig(name="example", url=httpserver.url_for("/"))
    result = await detector.check(blog)

    assert result.changed is True


async def test_sitemap_url_persisted_in_state(
    detector: ChangeDetector,
    httpserver: HTTPServer,
    state_repo: BlogStateRepository,
) -> None:
    html_content = read_fixture("html/feed_link_rss.html")
    feed_content = read_fixture("feeds/rss_valid.xml")
    sitemap_content = read_fixture("sitemap/urlset.xml")

    httpserver.expect_request("/").respond_with_data(
        html_content,
        status=200,
        headers={"Content-Type": "text/html; charset=utf-8"},
    )
    httpserver.expect_request("/feed.xml").respond_with_data(
        feed_content,
        status=200,
        headers={"Content-Type": "application/rss+xml"},
    )
    httpserver.expect_request("/robots.txt").respond_with_data(
        f"Sitemap: {httpserver.url_for('/sitemap.xml')}",
        status=200,
        headers={"Content-Type": "text/plain; charset=utf-8"},
    )
    httpserver.expect_request("/sitemap.xml").respond_with_data(
        sitemap_content,
        status=200,
        headers={"Content-Type": "application/xml"},
    )

    blog = BlogConfig(name="example", url=httpserver.url_for("/"))
    await detector.check(blog)

    persisted = state_repo.get(blog.blog_id)
    assert persisted is not None
    assert persisted.sitemap_url == httpserver.url_for("/sitemap.xml")
