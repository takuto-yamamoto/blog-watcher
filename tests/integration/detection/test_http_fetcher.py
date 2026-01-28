from collections.abc import AsyncIterator

import httpx
import pytest
import respx

from blog_watcher.detection.http_fetcher import HttpFetcher


@pytest.fixture
async def fetcher() -> AsyncIterator[HttpFetcher]:
    async with httpx.AsyncClient() as client:
        yield HttpFetcher(client)


@pytest.fixture
async def fetcher_with_redirects() -> AsyncIterator[HttpFetcher]:
    async with httpx.AsyncClient(follow_redirects=True) as client:
        yield HttpFetcher(client)


@pytest.mark.integration
class TestHttpFetcherIntegration:
    @respx.mock
    async def test_fetch_with_respx_mock_success(self, fetcher: HttpFetcher) -> None:
        url = "https://example.com/blog/feed.xml"
        content = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>Test Blog</title>
        <item>
            <title>Article</title>
        </item>
    </channel>
</rss>"""

        respx.get(url).mock(
            return_value=httpx.Response(
                200,
                text=content,
                headers={"Content-Type": "application/rss+xml", "ETag": '"feed-version-1"', "Last-Modified": "Mon, 27 Jan 2025 12:00:00 GMT"},
            )
        )

        result = await fetcher.fetch(url)

        assert result.status_code == 200
        assert result.content == content
        assert result.etag == '"feed-version-1"'
        assert result.last_modified == "Mon, 27 Jan 2025 12:00:00 GMT"
        assert result.is_modified is True

    @respx.mock
    async def test_fetch_handles_redirect(self, fetcher_with_redirects: HttpFetcher) -> None:
        original_url = "https://example.com/old-feed"
        redirect_url = "https://example.com/new-feed"
        content = "<rss>Redirected content</rss>"

        respx.get(original_url).mock(return_value=httpx.Response(301, headers={"Location": redirect_url}))
        respx.get(redirect_url).mock(return_value=httpx.Response(200, text=content))

        result = await fetcher_with_redirects.fetch(original_url)

        assert result.content == content

    @respx.mock
    async def test_conditional_get_with_etag(self, fetcher: HttpFetcher) -> None:
        url = "https://example.com/feed"
        etag = '"version-abc123"'
        content = "<rss>Content</rss>"

        respx.get(url).mock(return_value=httpx.Response(200, text=content, headers={"ETag": etag})).pass_through()

        result1 = await fetcher.fetch(url)
        assert result1.etag == etag
        assert result1.is_modified is True

        respx.clear()
        respx.get(url).mock(return_value=httpx.Response(304, headers={"ETag": etag}))

        result2 = await fetcher.fetch(url, etag=etag)
        assert result2.status_code == 304
        assert result2.content is None
        assert result2.is_modified is False

    @respx.mock
    async def test_conditional_get_with_last_modified(self, fetcher: HttpFetcher) -> None:
        url = "https://example.com/feed"
        last_modified = "Mon, 27 Jan 2025 10:00:00 GMT"
        content = "<rss>Content</rss>"

        respx.get(url).mock(return_value=httpx.Response(200, text=content, headers={"Last-Modified": last_modified})).pass_through()

        result1 = await fetcher.fetch(url)
        assert result1.last_modified == last_modified
        assert result1.is_modified is True

        respx.clear()
        respx.get(url).mock(return_value=httpx.Response(304, headers={"Last-Modified": last_modified}))

        result2 = await fetcher.fetch(url, last_modified=last_modified)
        assert result2.status_code == 304
        assert result2.content is None
        assert result2.is_modified is False
