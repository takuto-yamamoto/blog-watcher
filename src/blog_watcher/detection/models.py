from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DetectionResult:
    blog_id: str
    changed: bool
    http_status: int | None
    url_fingerprint: str | None


@dataclass(frozen=True, slots=True)
class DetectorConfig:
    feed_max_entries: int = 20
    extract_selector: str = "a[href]"
    normalize_lowercase_host: bool = True
    normalize_strip_tracking_params: bool = True
    normalize_strip_fragments: bool = True
    normalize_trailing_slash: bool = True
    normalize_force_https: bool = True


@dataclass(frozen=True, slots=True)
class FeedSnapshot:
    url: str
    entry_keys: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SitemapSnapshot:
    url: str
    url_fingerprint: str


@dataclass(frozen=True, slots=True)
class HtmlSnapshot:
    url_fingerprint: str
