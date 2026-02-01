from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from blog_watcher.detection.feed.detector import detect_feed_urls, parse_feed
from blog_watcher.detection.urls.fingerprinter import fingerprint_urls

if TYPE_CHECKING:
    from blog_watcher.detection.feed.detector import ParsedFeed
    from blog_watcher.detection.http_fetcher import Fetcher, FetchResult
    from blog_watcher.storage.models import BlogState


@dataclass(frozen=True, slots=True)
class FeedDetectionResult:
    feed_url: str | None
    entry_keys: tuple[str, ...]
    fingerprint: str
    changed: bool
    ok: bool


class FeedChangeDetector:
    def __init__(self, *, fetcher: Fetcher) -> None:
        self._fetcher = fetcher

    async def detect(self, fetch_result: FetchResult, base_url: str, previous_state: BlogState | None) -> FeedDetectionResult:
        discovery = detect_feed_urls(fetch_result.content, base_url)

        for feed_url in discovery.candidates:
            parsed = await self._try_fetch_and_parse(feed_url)
            if parsed is None:
                continue
            entry_keys = tuple(entry.id for entry in parsed.entries)
            fingerprint = fingerprint_urls(list(entry_keys))
            changed = self._detect_feed_changes(entry_keys, previous_state)
            return FeedDetectionResult(
                feed_url=feed_url,
                entry_keys=entry_keys,
                fingerprint=fingerprint,
                changed=changed,
                ok=True,
            )

        return FeedDetectionResult(
            feed_url=None,
            entry_keys=(),
            fingerprint="",
            changed=False,
            ok=False,
        )

    async def _try_fetch_and_parse(self, feed_url: str) -> ParsedFeed | None:
        feed_result = await self._fetcher.fetch(feed_url)
        if feed_result.content is None:
            return None
        return parse_feed(feed_result.content, feed_url)

    def _detect_feed_changes(self, entry_keys: tuple[str, ...], previous_state: BlogState | None) -> bool:
        if not entry_keys or previous_state is None:
            return False  # first-run handled by caller
        previous_entry_keys: tuple[str, ...] = ()
        if previous_state.recent_entry_keys:
            previous_entry_keys = tuple(json.loads(previous_state.recent_entry_keys))
        return entry_keys != previous_entry_keys
