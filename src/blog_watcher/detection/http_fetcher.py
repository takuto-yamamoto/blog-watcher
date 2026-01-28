from dataclasses import dataclass
from enum import StrEnum
from http import HTTPStatus

import httpx


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

        response = await self._client.get(url, headers=headers)

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
