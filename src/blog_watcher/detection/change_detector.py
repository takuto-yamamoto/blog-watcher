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
    feed_etag: str | None = None
    feed_last_modified: str | None = None
    sitemap_etag: str | None = None
    sitemap_last_modified: str | None = None


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
        previous_state = self._state_repo.get(blog.blog_id)
        fetch_result = await self._fetch_html(blog.url)

        feed_detector = FeedChangeDetector(fetcher=self._fetcher, config=self._config)
        feed_result = await feed_detector.detect(fetch_result, blog.url, previous_state)

        sitemap_result = None
        if not feed_result.changed:
            sitemap_detector = SitemapChangeDetector(fetcher=self._fetcher, config=self._config)
            sitemap_result = await sitemap_detector.detect(blog.url, previous_state)

        sitemap_changed = sitemap_result.changed if sitemap_result is not None else False
        changed = feed_result.changed or sitemap_changed

        is_initial = previous_state is None
        if is_initial:
            changed = True

        effective_fingerprint = sitemap_result.fingerprint if sitemap_result is not None and sitemap_result.fingerprint else feed_result.fingerprint

        context = _CheckContext(
            blog_id=blog.blog_id,
            fetch_result=fetch_result,
            feed_url=feed_result.feed_url,
            entry_keys=feed_result.entry_keys,
            fingerprint=effective_fingerprint,
            sitemap_url=sitemap_result.sitemap_url if sitemap_result is not None else None,
            feed_etag=feed_result.etag,
            feed_last_modified=feed_result.last_modified,
            sitemap_etag=sitemap_result.etag if sitemap_result is not None else None,
            sitemap_last_modified=sitemap_result.last_modified if sitemap_result is not None else None,
        )

        self._persist_state(context, changed=changed, previous_state=previous_state, is_initial=is_initial)
        return self._build_result(context, changed=changed, is_initial=is_initial)

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
        is_initial: bool,
    ) -> None:
        now = datetime.now(UTC)
        if is_initial:
            last_changed_at = previous_state.last_changed_at if previous_state else None
        elif changed:
            last_changed_at = now
        else:
            last_changed_at = previous_state.last_changed_at if previous_state else None
        new_state = BlogState(
            blog_id=context.blog_id,
            etag=context.fetch_result.etag,
            last_modified=context.fetch_result.last_modified,
            url_fingerprint=context.fingerprint,
            feed_url=context.feed_url,
            sitemap_url=context.sitemap_url,
            recent_entry_keys=json.dumps(list(context.entry_keys)),
            last_checked_at=now,
            last_changed_at=last_changed_at,
            consecutive_errors=0,
            feed_etag=context.feed_etag,
            feed_last_modified=context.feed_last_modified,
            sitemap_etag=context.sitemap_etag,
            sitemap_last_modified=context.sitemap_last_modified,
        )
        self._state_repo.upsert(new_state)

    def _build_result(self, context: _CheckContext, *, changed: bool, is_initial: bool) -> DetectionResult:
        return DetectionResult(
            blog_id=context.blog_id,
            changed=changed,
            http_status=context.fetch_result.status_code,
            url_fingerprint=context.fingerprint,
            is_initial=is_initial,
        )
