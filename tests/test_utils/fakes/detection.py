from __future__ import annotations

from typing import TYPE_CHECKING

from tests.test_utils.factories import FetchResultFactory

if TYPE_CHECKING:
    from blog_watcher.detection.http_fetcher import FetchResult
    from blog_watcher.storage.models import BlogState


class FakeFetcher:
    def __init__(self, results: dict[str, FetchResult]) -> None:
        self._results = results
        self.fetched_urls: list[str] = []

    async def fetch(
        self,
        url: str,
        *,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> FetchResult:
        _ = etag, last_modified
        self.fetched_urls.append(url)
        if url not in self._results:
            return FetchResultFactory.build(content=None)
        return self._results[url]


class FakeBlogStateRepository:
    def __init__(self, initial: dict[str, BlogState] | None = None) -> None:
        self._states = dict(initial or {})

    def get(self, blog_id: str) -> BlogState | None:
        return self._states.get(blog_id)

    def upsert(self, state: BlogState) -> None:
        self._states[state.blog_id] = state
