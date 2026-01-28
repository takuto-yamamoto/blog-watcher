import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from enum import StrEnum
from http import HTTPStatus

import httpx
from tenacity import (
    AsyncRetrying,
    RetryCallState,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


class HTTPHeader(StrEnum):
    IF_NONE_MATCH = "If-None-Match"
    IF_MODIFIED_SINCE = "If-Modified-Since"
    ETAG = "ETag"
    LAST_MODIFIED = "Last-Modified"
    RETRY_AFTER = "Retry-After"


class RetriableHTTPError(Exception):
    def __init__(self, response: httpx.Response) -> None:
        self.response = response
        super().__init__(f"Retriable HTTP error: {response.status_code}")


@dataclass(frozen=True, slots=True)
class FetchResult:
    status_code: int
    content: str | None
    etag: str | None
    last_modified: str | None
    is_modified: bool


_DEFAULT_RETRY_AFTER: float = 60.0
_EXPONENTIAL_MAX = 60
_EXPONENTIAL_MIN = 1
_exponential_backoff = wait_exponential(multiplier=_EXPONENTIAL_MIN, max=_EXPONENTIAL_MAX)


def parse_retry_after(header: str) -> float:
    try:
        return float(header)
    except ValueError:
        pass
    try:
        dt = parsedate_to_datetime(header)
        return max(0.0, dt.timestamp() - time.time())
    except (ValueError, TypeError):
        return _DEFAULT_RETRY_AFTER


def wait_strategy(retry_state: RetryCallState) -> float:
    outcome = retry_state.outcome
    if outcome is None:
        return float(_exponential_backoff(retry_state=retry_state))

    exc = outcome.exception()
    if isinstance(exc, RetriableHTTPError) and exc.response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
        retry_after = exc.response.headers.get(HTTPHeader.RETRY_AFTER)
        if retry_after is None:
            return _DEFAULT_RETRY_AFTER
        return parse_retry_after(retry_after)

    return float(_exponential_backoff(retry_state=retry_state))


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
            retry=retry_if_exception_type((httpx.TimeoutException, RetriableHTTPError)),
            wait=wait_strategy,
            stop=stop_after_attempt(3),
            reraise=True,
        ):
            with attempt:
                response = await self._client.get(url, headers=headers)
                if response.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
                    raise RetriableHTTPError(response)
                if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
                    raise RetriableHTTPError(response)

        if response.status_code == HTTPStatus.NOT_MODIFIED:
            return FetchResult(
                status_code=HTTPStatus.NOT_MODIFIED,
                content=None,
                etag=response.headers.get(HTTPHeader.ETAG),
                last_modified=response.headers.get(HTTPHeader.LAST_MODIFIED),
                is_modified=False,
            )

        return FetchResult(
            status_code=response.status_code,
            content=response.text,
            etag=response.headers.get(HTTPHeader.ETAG),
            last_modified=response.headers.get(HTTPHeader.LAST_MODIFIED),
            is_modified=True,
        )
