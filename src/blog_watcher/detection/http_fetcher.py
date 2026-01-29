from dataclasses import dataclass
from enum import StrEnum
from http import HTTPStatus

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from blog_watcher.observability import get_logger

logger = get_logger(__name__)


class HTTPHeader(StrEnum):
    IF_NONE_MATCH = "If-None-Match"
    IF_MODIFIED_SINCE = "If-Modified-Since"
    ETAG = "ETag"
    LAST_MODIFIED = "Last-Modified"


@dataclass(frozen=True, slots=True)
class FetchResult:
    status_code: int
    content: str | None
    etag: str | None
    last_modified: str | None
    is_modified: bool


class HttpFetcher:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def fetch(
        self,
        url: str,
        *,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> FetchResult:
        headers: dict[str, str] = {}
        if etag is not None:
            headers[HTTPHeader.IF_NONE_MATCH] = etag
        if last_modified is not None:
            headers[HTTPHeader.IF_MODIFIED_SINCE] = last_modified

        async for attempt in AsyncRetrying(
            retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
            wait=wait_exponential(multiplier=1, max=60),
            stop=stop_after_attempt(3),
            reraise=True,
        ):
            with attempt:
                response = await self._client.get(url, headers=headers)
                if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
                    logger.warning("fetch_rate_limited", url=url)
                    response.raise_for_status()
                if response.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
                    logger.warning("fetch_server_error", url=url, status_code=response.status_code)
                    response.raise_for_status()

        if response.status_code == HTTPStatus.NOT_MODIFIED:
            logger.info("fetch_not_modified", url=url)
            return FetchResult(
                status_code=HTTPStatus.NOT_MODIFIED,
                content=None,
                etag=response.headers.get(HTTPHeader.ETAG),
                last_modified=response.headers.get(HTTPHeader.LAST_MODIFIED),
                is_modified=False,
            )

        logger.info("fetch_succeeded", url=url, status_code=response.status_code)
        return FetchResult(
            status_code=response.status_code,
            content=response.text,
            etag=response.headers.get(HTTPHeader.ETAG),
            last_modified=response.headers.get(HTTPHeader.LAST_MODIFIED),
            is_modified=True,
        )
