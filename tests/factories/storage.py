from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

from blog_watcher.storage.models import BlogState, CheckHistory


def make_blog_state(**overrides: Any) -> BlogState:
    base = BlogState(
        blog_id="blog-1",
        etag=None,
        last_modified=None,
        url_fingerprint=None,
        feed_url=None,
        sitemap_url=None,
        recent_entry_keys=None,
        last_checked_at=datetime(2024, 1, 1, tzinfo=UTC),
        last_changed_at=None,
        consecutive_errors=0,
    )
    return replace(base, **overrides)


def make_check_history(**overrides: Any) -> CheckHistory:
    base = CheckHistory(
        blog_id="blog-1",
        checked_at=datetime(2024, 1, 1, tzinfo=UTC),
        http_status=200,
        skipped=False,
        changed=False,
        url_fingerprint=None,
        error_message=None,
    )
    return replace(base, **overrides)
