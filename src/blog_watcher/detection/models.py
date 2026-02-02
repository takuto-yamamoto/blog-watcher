from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from blog_watcher.detection.urls.normalizer import NormalizationConfig


def is_cache_fresh(
    last_checked_at: datetime | None,
    ttl_days: int,
    *,
    now: datetime | None = None,
) -> bool:
    if last_checked_at is None:
        return False
    now = now or datetime.now(UTC)
    return (now - last_checked_at) < timedelta(days=ttl_days)


@dataclass(frozen=True, slots=True)
class DetectionResult:
    blog_id: str
    changed: bool
    http_status: int | None
    url_fingerprint: str | None


@dataclass(frozen=True, slots=True)
class DetectorConfig:
    cache_ttl_days: int = 7
    feed_max_entries: int = 20
    extract_selector: str = "a[href]"
    normalize_lowercase_host: bool = True
    normalize_strip_tracking_params: bool = True
    normalize_strip_fragments: bool = True
    normalize_trailing_slash: bool = True
    normalize_force_https: bool = True

    def to_normalization_config(self) -> NormalizationConfig:
        return NormalizationConfig(
            lowercase_host=self.normalize_lowercase_host,
            strip_tracking_params=self.normalize_strip_tracking_params,
            strip_fragments=self.normalize_strip_fragments,
            normalize_trailing_slash=self.normalize_trailing_slash,
            force_https=self.normalize_force_https,
        )


@dataclass(frozen=True, slots=True)
class FeedSnapshot:
    url: str
    entry_keys: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SitemapSnapshot:
    url: str
    page_urls: tuple[str, ...]
    url_fingerprint: str


@dataclass(frozen=True, slots=True)
class HtmlSnapshot:
    url_fingerprint: str
