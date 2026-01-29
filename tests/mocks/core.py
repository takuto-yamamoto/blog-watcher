from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from blog_watcher.notifications import Notification, Notifier

if TYPE_CHECKING:
    from collections.abc import Iterable

    from blog_watcher.config import BlogConfig
    from blog_watcher.detection import DetectionResult


class CountingWatcher:
    def __init__(self) -> None:
        self.calls = 0

    async def check_all(self) -> None:
        self.calls += 1


class BlockingWatcher:
    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.finished = asyncio.Event()

    async def check_all(self) -> None:
        self.started.set()
        await asyncio.sleep(0.5)
        self.finished.set()


class SequenceDetector:
    def __init__(self, results: Iterable[DetectionResult]) -> None:
        self._results = iter(results)
        self.calls: list[str] = []

    async def check(self, blog: BlogConfig) -> DetectionResult:
        self.calls.append(blog.url)
        try:
            return next(self._results)
        except StopIteration as exc:
            msg = "Detector results exhausted"
            raise RuntimeError(msg) from exc


class CapturingNotifier(Notifier):
    def __init__(self) -> None:
        self.notifications: list[Notification] = []

    async def send(self, notification: Notification) -> None:
        self.notifications.append(notification)
