from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from blog_watcher.config.models import BlogConfig
from tests.conftest import read_fixture

if TYPE_CHECKING:
    from pytest_httpserver import HTTPServer

    from blog_watcher.detection.change_detector import ChangeDetector

pytestmark = [pytest.mark.integration]


async def test_first_check_with_rss_feed_detects_new_entries(
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
    result = await detector.check(blog)

    assert result.blog_id == "example"
    assert result.changed is True
    assert result.http_status == 200
    assert result.url_fingerprint is not None


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
    httpserver.clear()
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
