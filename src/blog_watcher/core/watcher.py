from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol

from blog_watcher.notification import Notification, Notifier
from blog_watcher.storage import BlogState, BlogStateRepository, CheckHistory, CheckHistoryRepository

if TYPE_CHECKING:
    from blog_watcher.config import AppConfig, BlogConfig
    from blog_watcher.detection.models import DetectionResult


class Detector(Protocol):
    async def check(self, blog: BlogConfig) -> DetectionResult: ...


class BlogWatcher:
    def __init__(
        self,
        *,
        config: AppConfig,
        detector: Detector,
        notifier: Notifier,
        state_repo: BlogStateRepository,
        history_repo: CheckHistoryRepository,
    ) -> None:
        self._config = config
        self._detector = detector
        self._notifier = notifier
        self._state_repo = state_repo
        self._history_repo = history_repo

    async def check_all(self) -> None:
        for blog in self._config.blogs:
            result = await self._detector.check(blog)
            self._persist_result(result)
            if result.changed:
                await self._notifier.send(Notification(title=f"Blog updated: {blog.name}", body=blog.url, url=blog.url))

    def _persist_result(self, result: DetectionResult) -> None:
        now = datetime.now(UTC)
        state = self._state_repo.get(result.blog_id)
        if state is None:
            state = BlogState(
                blog_id=result.blog_id,
                etag=None,
                last_modified=None,
                url_fingerprint=result.url_fingerprint,
                feed_url=None,
                sitemap_url=None,
                recent_entry_keys=None,
                last_checked_at=now,
                last_changed_at=now if result.changed else None,
                consecutive_errors=0,
            )
        else:
            state = replace(
                state,
                url_fingerprint=result.url_fingerprint,
                last_checked_at=now,
                last_changed_at=now if result.changed else state.last_changed_at,
            )
        self._state_repo.upsert(state)

        history = CheckHistory(
            blog_id=result.blog_id,
            checked_at=now,
            http_status=result.http_status,
            skipped=False,
            changed=result.changed,
            url_fingerprint=result.url_fingerprint,
            error_message=None,
        )
        self._history_repo.add(history)
