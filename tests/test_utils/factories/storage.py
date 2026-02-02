from __future__ import annotations

from datetime import UTC, datetime

from factory.base import Factory

from blog_watcher.storage.models import BlogState, CheckHistory


class BlogStateFactory(Factory[BlogState]):
    class Meta:
        model = BlogState

    blog_id = "https://example.com"
    etag = None
    last_modified = None
    url_fingerprint = None
    feed_url = None
    sitemap_url = None
    recent_entry_keys = None
    last_checked_at = datetime(2024, 1, 1, tzinfo=UTC)
    last_changed_at = None
    consecutive_errors = 0
    feed_etag = None
    feed_last_modified = None
    sitemap_etag = None
    sitemap_last_modified = None


class CheckHistoryFactory(Factory[CheckHistory]):
    class Meta:
        model = CheckHistory

    blog_id = "https://example.com"
    checked_at = datetime(2024, 1, 1, tzinfo=UTC)
    http_status = 200
    skipped = False
    changed = False
    url_fingerprint = None
    error_message = None
