from collections.abc import AsyncIterator

import httpx
import pytest
import respx

from blog_watcher.detection.http_fetcher import HttpFetcher


@pytest.fixture
async def fetcher() -> AsyncIterator[HttpFetcher]:
    async with httpx.AsyncClient() as client:
        yield HttpFetcher(client)


class TestHttpFetcher:
    @respx.mock
    async def test_fetch_success_returns_content(self, fetcher: HttpFetcher) -> None:
        url = "https://example.com/feed"
        body = "<html><body>Hello</body></html>"
        respx.get(url).mock(return_value=httpx.Response(200, text=body))

        result = await fetcher.fetch(url)

        assert result.status_code == 200
        assert result.content == body
        assert result.etag is None
        assert result.last_modified is None
        assert result.is_modified is True

    @respx.mock
    async def test_fetch_captures_etag(self, fetcher: HttpFetcher) -> None:
        url = "https://example.com/feed"
        etag_value = '"abc123"'
        respx.get(url).mock(return_value=httpx.Response(200, text="content", headers={"ETag": etag_value}))

        result = await fetcher.fetch(url)

        assert result.etag == etag_value

    @respx.mock
    async def test_fetch_captures_last_modified(self, fetcher: HttpFetcher) -> None:
        url = "https://example.com/feed"
        last_modified_value = "Wed, 21 Oct 2015 07:28:00 GMT"
        respx.get(url).mock(return_value=httpx.Response(200, text="content", headers={"Last-Modified": last_modified_value}))

        result = await fetcher.fetch(url)

        assert result.last_modified == last_modified_value

    @respx.mock
    async def test_fetch_sends_if_none_match(self, fetcher: HttpFetcher) -> None:
        url = "https://example.com/feed"
        etag_value = '"abc123"'
        route = respx.get(url).mock(return_value=httpx.Response(200, text="content"))

        await fetcher.fetch(url, etag=etag_value)

        assert route.calls[0].request.headers.get("If-None-Match") == etag_value

    @respx.mock
    async def test_fetch_sends_if_modified_since(self, fetcher: HttpFetcher) -> None:
        url = "https://example.com/feed"
        last_modified_value = "Wed, 21 Oct 2015 07:28:00 GMT"
        route = respx.get(url).mock(return_value=httpx.Response(200, text="content"))

        await fetcher.fetch(url, last_modified=last_modified_value)

        assert route.calls[0].request.headers.get("If-Modified-Since") == last_modified_value

    @respx.mock
    async def test_fetch_304_returns_not_modified(self, fetcher: HttpFetcher) -> None:
        url = "https://example.com/feed"
        respx.get(url).mock(return_value=httpx.Response(304))

        result = await fetcher.fetch(url, etag='"abc123"')

        assert result.status_code == 304
        assert result.content is None
        assert result.is_modified is False

    @respx.mock
    async def test_fetch_retries_on_timeout(self, fetcher: HttpFetcher) -> None:
        url = "https://example.com/feed"
        route = respx.get(url).mock(
            side_effect=[
                httpx.ReadTimeout("Timeout"),
                httpx.Response(200, text="success"),
            ]
        )

        result = await fetcher.fetch(url)

        assert result.content == "success"
        assert route.call_count == 2

    @respx.mock
    async def test_fetch_retries_on_5xx(self, fetcher: HttpFetcher) -> None:
        url = "https://example.com/feed"
        route = respx.get(url).mock(
            side_effect=[
                httpx.Response(503, text="Service Unavailable"),
                httpx.Response(200, text="success"),
            ]
        )

        result = await fetcher.fetch(url)

        assert result.content == "success"
        assert route.call_count == 2

    @respx.mock
    async def test_fetch_raises_after_max_retries(self, fetcher: HttpFetcher) -> None:
        url = "https://example.com/feed"
        respx.get(url).mock(side_effect=httpx.ReadTimeout("Timeout"))

        with pytest.raises(httpx.ReadTimeout):
            await fetcher.fetch(url)

    @respx.mock
    async def test_fetch_no_retry_on_4xx(self, fetcher: HttpFetcher) -> None:
        url = "https://example.com/feed"
        route = respx.get(url).mock(return_value=httpx.Response(404, text="Not Found"))

        result = await fetcher.fetch(url)

        assert result.status_code == 404
        assert route.call_count == 1

    @respx.mock
    async def test_fetch_preserves_encoding(self, fetcher: HttpFetcher) -> None:
        url = "https://example.com/feed"
        content = "Hello 世界 🌍"
        respx.get(url).mock(return_value=httpx.Response(200, text=content, headers={"Content-Type": "text/html; charset=utf-8"}))

        result = await fetcher.fetch(url)

        assert result.content == content
