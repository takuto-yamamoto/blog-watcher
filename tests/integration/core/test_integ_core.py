from datetime import UTC, datetime
from pathlib import Path

import pytest
from freezegun import freeze_time

from blog_watcher.config import AppConfig, BlogConfig, SlackConfig
from blog_watcher.core import BlogWatcher
from blog_watcher.detection import DetectionResult
from blog_watcher.storage import BlogState, BlogStateRepository, CheckHistory, CheckHistoryRepository, Database
from tests.mocks.core import CapturingNotifier, SequenceDetector

pytestmark = [pytest.mark.integration]


@freeze_time("2025-01-27T12:00:00Z")
async def test_check_cycle_persists_state_and_history(tmp_path: Path) -> None:
    db = Database(tmp_path / "test.db")
    db.initialize()
    state_repo = BlogStateRepository(db)
    history_repo = CheckHistoryRepository(db)

    now = datetime.now(UTC)
    blog_id = "https://example.com/blog"
    results = [
        DetectionResult(blog_id=blog_id, changed=True, http_status=200, url_fingerprint="fp-1"),
        DetectionResult(blog_id=blog_id, changed=False, http_status=304, url_fingerprint="fp-1"),
    ]
    detector = SequenceDetector(results)
    notifier = CapturingNotifier()

    config = AppConfig(
        slack=SlackConfig(webhook_url="https://example.invalid/webhook"),
        blogs=[BlogConfig(name="Example Blog", url="https://example.com/blog")],
    )

    watcher = BlogWatcher(
        config=config,
        detector=detector,
        notifier=notifier,
        state_repo=state_repo,
        history_repo=history_repo,
    )

    try:
        await watcher.check_all()
        await watcher.check_all()

        state = state_repo.get(blog_id)
        assert isinstance(state, BlogState)
        assert state.url_fingerprint == "fp-1"
        assert state.last_checked_at == now

        history = history_repo.list_by_blog_id(blog_id)
        assert len(history) == 2
        assert isinstance(history[-1], CheckHistory)
        assert history[-1].checked_at == now

        assert len(notifier.notifications) == 1
    finally:
        db.close()
