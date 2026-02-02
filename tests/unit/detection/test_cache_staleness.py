from __future__ import annotations

from datetime import UTC, datetime, timedelta

from blog_watcher.detection.models import is_cache_fresh


def test_is_cache_fresh_within_ttl() -> None:
    now = datetime(2024, 6, 15, tzinfo=UTC)
    last_checked = now - timedelta(days=3)
    assert is_cache_fresh(last_checked, ttl_days=7, now=now) is True


def test_is_cache_stale_after_ttl() -> None:
    now = datetime(2024, 6, 15, tzinfo=UTC)
    last_checked = now - timedelta(days=8)
    assert is_cache_fresh(last_checked, ttl_days=7, now=now) is False
