import asyncio

import pytest
from tests.mocks.core import CountingWatcher

from blog_watcher.core import WatcherScheduler

pytestmark = [pytest.mark.integration]


@pytest.mark.slow
async def test_scheduler_runs_job_on_interval() -> None:
    watcher = CountingWatcher()
    scheduler = WatcherScheduler(interval_seconds=1, watcher=watcher)

    await scheduler.start()
    await asyncio.sleep(2.5)
    await scheduler.shutdown()

    assert watcher.calls == 2
