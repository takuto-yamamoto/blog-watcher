from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol

from blog_watcher.detection.feed_detector import ParsedFeed, detect_feed_urls, parse_feed
from blog_watcher.detection.models import DetectionResult, DetectorConfig
from blog_watcher.detection.url_fingerprinter import fingerprint_urls
from blog_watcher.storage.models import BlogState

if TYPE_CHECKING:
    from blog_watcher.config import BlogConfig
    from blog_watcher.detection.http_fetcher import FetchResult


class Fetcher(Protocol):
    async def fetch(self, url: str) -> FetchResult: ...


class StateRepository(Protocol):
    def get(self, blog_id: str) -> BlogState | None: ...
    def upsert(self, state: BlogState) -> None: ...


@dataclass(frozen=True, slots=True)
class _CheckContext:
    blog_id: str
    fetch_result: FetchResult
    feed_url: str
    entry_keys: tuple[str, ...]
    fingerprint: str


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
        feed_url = await self._detect_feed_url(fetch_result, blog.url)
        parsed_feed = await self._fetch_and_parse_feed(feed_url)
        entry_keys = self._extract_entry_keys(parsed_feed)
        fingerprint = self._compute_fingerprint(parsed_feed)

        context = _CheckContext(
            blog_id=blog.blog_id,
            fetch_result=fetch_result,
            feed_url=feed_url,
            entry_keys=entry_keys,
            fingerprint=fingerprint,
        )

        previous_state = self._load_previous_state(context.blog_id)
        changed = self._detect_changes(context.entry_keys, previous_state)
        self._persist_state(context, changed=changed, previous_state=previous_state)
        return self._build_result(context, changed=changed)

    async def _fetch_html(self, url: str) -> FetchResult:
        result = await self._fetcher.fetch(url)
        if result.content is None:
            msg = "fetch_result.content is None"
            raise ValueError(msg)
        return result

    async def _detect_feed_url(self, fetch_result: FetchResult, base_url: str) -> str:
        feed_urls = detect_feed_urls(fetch_result.content, base_url)
        if not feed_urls:
            msg = "No feed URLs detected"
            raise ValueError(msg)
        return feed_urls[0]

    async def _fetch_and_parse_feed(self, feed_url: str) -> ParsedFeed:
        feed_result = await self._fetcher.fetch(feed_url)
        if feed_result.content is None:
            msg = "feed_result.content is None"
            raise ValueError(msg)
        parsed_feed = parse_feed(feed_result.content, feed_url)
        if parsed_feed is None:
            msg = "Failed to parse feed"
            raise ValueError(msg)
        return parsed_feed

    def _extract_entry_keys(self, parsed_feed: ParsedFeed) -> tuple[str, ...]:
        return tuple(entry.id for entry in parsed_feed.entries)

    def _load_previous_state(self, blog_id: str) -> BlogState | None:
        return self._state_repo.get(blog_id)

    def _detect_changes(self, entry_keys: tuple[str, ...], previous_state: BlogState | None) -> bool:
        if previous_state is None:
            return True
        previous_entry_keys: tuple[str, ...] = ()
        if previous_state.recent_entry_keys:
            previous_entry_keys = tuple(json.loads(previous_state.recent_entry_keys))
        return entry_keys != previous_entry_keys

    def _compute_fingerprint(self, parsed_feed: ParsedFeed) -> str:
        return fingerprint_urls([entry.id for entry in parsed_feed.entries])

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
            sitemap_url=None,
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
