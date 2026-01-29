from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Awaitable


class WatcherScheduler:
    def __init__(self, interval_seconds: int, watcher: object) -> None:
        if interval_seconds <= 0:
            msg = "interval_seconds must be positive"
            raise ValueError(msg)
        if not hasattr(watcher, "check_all"):
            msg = "watcher must define check_all"
            raise TypeError(msg)

        self._interval_seconds = interval_seconds
        self._watcher = watcher
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run())

    async def shutdown(self) -> None:
        if self._task is None:
            return
        self._stop_event.set()
        await self._task
        self._task = None

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            await asyncio.sleep(self._interval_seconds)
            if self._stop_event.is_set():
                break
            await self._maybe_await(self._watcher.check_all())

    async def _maybe_await(self, result: Awaitable[object] | object) -> None:
        if asyncio.iscoroutine(result):
            await result
