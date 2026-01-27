from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True, slots=True)
class BlogState:
    blog_id: str
    etag: str | None
    last_modified: str | None
    url_fingerprint: str | None
    feed_url: str | None
    sitemap_url: str | None
    recent_entry_keys: str | None
    last_checked_at: datetime
    last_changed_at: datetime | None
    consecutive_errors: int = 0

    def __post_init__(self) -> None:
        if not self.blog_id:
            msg = "blog_id cannot be empty"
            raise ValueError(msg)
        if self.consecutive_errors < 0:
            msg = "consecutive_errors cannot be negative"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class CheckHistory:
    blog_id: str
    checked_at: datetime
    http_status: int | None
    skipped: bool
    changed: bool
    url_fingerprint: str | None
    error_message: str | None
