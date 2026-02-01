from collections.abc import AsyncIterator

import httpx
import pytest
from pytest_httpserver import HTTPServer
from werkzeug import Request, Response

from blog_watcher.detection.http_fetcher import HttpFetcher
from tests.test_utils.helpers import read_fixture


@pytest.fixture
async def fetcher(httpserver: HTTPServer) -> AsyncIterator[HttpFetcher]:
    async with httpx.AsyncClient(base_url=httpserver.url_for("/")) as client:
        yield HttpFetcher(client)


@pytest.fixture
async def fetcher_with_redirects(httpserver: HTTPServer) -> AsyncIterator[HttpFetcher]:
    async with httpx.AsyncClient(base_url=httpserver.url_for("/"), follow_redirects=True) as client:
        yield HttpFetcher(client)


@pytest.mark.integration
class TestHttpFetcherIntegrationSuite:
    async def test_fetch_success(self, fetcher: HttpFetcher, httpserver: HTTPServer) -> None:
        content = read_fixture("feeds/rss_valid.xml")

        httpserver.expect_request("/feed.xml").respond_with_data(
            content,
            status=200,
            headers={
                "Content-Type": "application/rss+xml",
                "ETag": '"feed-version-1"',
                "Last-Modified": "Mon, 27 Jan 2025 12:00:00 GMT",
            },
        )

        result = await fetcher.fetch("/feed.xml")

        assert result.status_code == 200
        assert result.content == content
        assert result.etag == '"feed-version-1"'
        assert result.last_modified == "Mon, 27 Jan 2025 12:00:00 GMT"
        assert result.is_modified is True

    async def test_fetch_handles_redirect(self, fetcher_with_redirects: HttpFetcher, httpserver: HTTPServer) -> None:
        content = read_fixture("feeds/rss_valid.xml")

        httpserver.expect_request("/old-feed").respond_with_data("", status=301, headers={"Location": httpserver.url_for("/new-feed")})
        httpserver.expect_request("/new-feed").respond_with_data(content, status=200)

        result = await fetcher_with_redirects.fetch("/old-feed")

        assert result.content == content

    async def test_conditional_get_with_etag(self, fetcher: HttpFetcher, httpserver: HTTPServer) -> None:
        content = read_fixture("feeds/rss_valid.xml")
        etag = '"version-abc123"'

        def etag_handler(request: Request) -> Response:
            if request.headers.get("If-None-Match") == etag:
                return Response("", status=304, headers={"ETag": etag})
            return Response(content, status=200, headers={"ETag": etag})

        httpserver.expect_ordered_request("/feed").respond_with_handler(etag_handler)
        httpserver.expect_ordered_request("/feed").respond_with_handler(etag_handler)

        result1 = await fetcher.fetch("/feed")
        assert result1.etag == etag
        assert result1.is_modified is True

        result2 = await fetcher.fetch("/feed", etag=etag)
        assert result2.status_code == 304
        assert result2.content is None
        assert result2.is_modified is False

    async def test_conditional_get_with_last_modified(self, fetcher: HttpFetcher, httpserver: HTTPServer) -> None:
        content = read_fixture("feeds/rss_valid.xml")
        last_modified = "Mon, 27 Jan 2025 10:00:00 GMT"

        def last_modified_handler(request: Request) -> Response:
            if request.headers.get("If-Modified-Since") == last_modified:
                return Response("", status=304, headers={"Last-Modified": last_modified})
            return Response(content, status=200, headers={"Last-Modified": last_modified})

        httpserver.expect_ordered_request("/feed").respond_with_handler(last_modified_handler)
        httpserver.expect_ordered_request("/feed").respond_with_handler(last_modified_handler)

        result1 = await fetcher.fetch("/feed")
        assert result1.last_modified == last_modified
        assert result1.is_modified is True

        result2 = await fetcher.fetch("/feed", last_modified=last_modified)
        assert result2.status_code == 304
        assert result2.content is None
        assert result2.is_modified is False

    async def test_fetch_retries_on_429(self, fetcher: HttpFetcher, httpserver: HTTPServer) -> None:
        content = read_fixture("feeds/rss_valid.xml")

        httpserver.expect_ordered_request("/feed").respond_with_data("", status=429)
        httpserver.expect_ordered_request("/feed").respond_with_data(content, status=200)

        result = await fetcher.fetch("/feed")

        assert result.status_code == 200
        assert result.content == content
