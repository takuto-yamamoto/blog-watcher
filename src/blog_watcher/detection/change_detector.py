from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol

from blog_watcher.detection.feed import FeedChangeDetector
from blog_watcher.detection.models import DetectionResult, DetectorConfig
from blog_watcher.detection.sitemap import SitemapChangeDetector
from blog_watcher.storage.models import BlogState

if TYPE_CHECKING:
    from blog_watcher.config import BlogConfig
    from blog_watcher.detection.http_fetcher import Fetcher, FetchResult


class StateRepository(Protocol):
    def get(self, blog_id: str) -> BlogState | None: ...
    def upsert(self, state: BlogState) -> None: ...


@dataclass(frozen=True, slots=True)
class _CheckContext:
    blog_id: str
    fetch_result: FetchResult
    feed_url: str | None
    entry_keys: tuple[str, ...]
    fingerprint: str
    sitemap_url: str | None


class ChangeDetector:
    def __init__(
        self,
        *,
        fetcher: Fetcher,
        state_repo: StateRepository,
        config: DetectorConfig | None = None,
    ) -> None:
        self._fetcher = fetcher
        self._state_repo = state_repo
        self._config = config or DetectorConfig()

    async def check(self, blog: BlogConfig) -> DetectionResult:
        fetch_result = await self._fetch_html(blog.url)
        previous_state = self._state_repo.get(blog.blog_id)

        feed_detector = FeedChangeDetector(fetcher=self._fetcher, config=self._config)
        feed_result = await feed_detector.detect(fetch_result, blog.url, previous_state)

        sitemap_result = None
        if not feed_result.changed:
            sitemap_detector = SitemapChangeDetector(fetcher=self._fetcher, config=self._config)
            sitemap_result = await sitemap_detector.detect(blog.url, previous_state)

        sitemap_changed = sitemap_result.changed if sitemap_result is not None else False
        changed = feed_result.changed or sitemap_changed

        # First run with no previous state is always changed
        if not changed and previous_state is None:
            changed = True

        effective_fingerprint = sitemap_result.fingerprint if sitemap_result is not None and sitemap_result.fingerprint else feed_result.fingerprint

        context = _CheckContext(
            blog_id=blog.blog_id,
            fetch_result=fetch_result,
            feed_url=feed_result.feed_url,
            entry_keys=feed_result.entry_keys,
            fingerprint=effective_fingerprint,
            sitemap_url=sitemap_result.sitemap_url if sitemap_result is not None else None,
        )

        self._persist_state(context, changed=changed, previous_state=previous_state)
        return self._build_result(context, changed=changed)

    async def _fetch_html(self, url: str) -> FetchResult:
        result = await self._fetcher.fetch(url)
        if result.content is None:
            msg = "fetch_result.content is None"
            raise ValueError(msg)
        return result

    def _persist_state(
        self,
        context: _CheckContext,
        *,
        changed: bool,
        previous_state: BlogState | None,
    ) -> None:
        now = datetime.now(UTC)
        new_state = BlogState(
            blog_id=context.blog_id,
            etag=context.fetch_result.etag,
            last_modified=context.fetch_result.last_modified,
            url_fingerprint=context.fingerprint,
            feed_url=context.feed_url,
            sitemap_url=context.sitemap_url,
            recent_entry_keys=json.dumps(list(context.entry_keys)),
            last_checked_at=now,
            last_changed_at=now if changed else previous_state.last_changed_at if previous_state else None,
            consecutive_errors=0,
        )
        self._state_repo.upsert(new_state)

    def _build_result(self, context: _CheckContext, *, changed: bool) -> DetectionResult:
        return DetectionResult(
            blog_id=context.blog_id,
            changed=changed,
            http_status=context.fetch_result.status_code,
            url_fingerprint=context.fingerprint,
        )
