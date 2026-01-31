import asyncio

import pytest

from blog_watcher.core import WatcherScheduler
from tests.mocks.core import CountingWatcher

pytestmark = [pytest.mark.integration]


@pytest.mark.slow
async def test_scheduler_runs_job_on_interval() -> None:
    watcher = CountingWatcher()
    scheduler = WatcherScheduler(interval_seconds=1, watcher=watcher)

    await scheduler.start()
    await asyncio.sleep(2.5)
    await scheduler.shutdown()

    assert watcher.calls == 2


@pytest.mark.slow
async def test_double_start_does_not_duplicate_loop() -> None:
    watcher = CountingWatcher()
    scheduler = WatcherScheduler(interval_seconds=1, watcher=watcher)

    await scheduler.start()
    await scheduler.start()
    await asyncio.sleep(2.5)
    await scheduler.shutdown()

    assert watcher.calls == 2
