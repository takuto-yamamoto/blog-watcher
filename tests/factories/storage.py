from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from blog_watcher.storage import BlogState, CheckHistory


def make_blog_state(**overrides: object) -> BlogState:
    base = BlogState(
        blog_id="blog-1",
        etag=None,
        last_modified=None,
        url_fingerprint=None,
        feed_url=None,
        sitemap_url=None,
        recent_entry_keys=None,
        last_checked_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        last_changed_at=None,
        consecutive_errors=0,
    )
    return replace(base, **overrides)


def make_check_history(**overrides: object) -> CheckHistory:
    base = CheckHistory(
        blog_id="blog-1",
        checked_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        http_status=200,
        skipped=False,
        changed=False,
        url_fingerprint=None,
        error_message=None,
    )
    return replace(base, **overrides)
