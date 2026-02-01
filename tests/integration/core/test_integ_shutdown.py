import pytest

from blog_watcher.core import WatcherScheduler
from tests.test_utils.mocks.core import BlockingWatcher

pytestmark = [pytest.mark.integration]


async def test_shutdown_completes_inflight_job() -> None:
    watcher = BlockingWatcher()
    scheduler = WatcherScheduler(interval_seconds=1, watcher=watcher)

    await scheduler.start()
    await watcher.started.wait()
    await scheduler.shutdown()

    assert watcher.finished.is_set()
