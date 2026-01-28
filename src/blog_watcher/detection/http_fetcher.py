from dataclasses import dataclass

import httpx


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
        msg = "Stub implementation"
        raise NotImplementedError(msg)
