import pytest
from tests.mocks.core import CountingWatcher

from blog_watcher.core import WatcherScheduler


class TestWatcherSchedulerValidation:
    def test_zero_interval_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="interval_seconds must be positive"):
            WatcherScheduler(0, CountingWatcher())

    def test_negative_interval_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="interval_seconds must be positive"):
            WatcherScheduler(-1, CountingWatcher())

    def test_watcher_without_check_all_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="watcher must define check_all"):
            WatcherScheduler(1, object())
