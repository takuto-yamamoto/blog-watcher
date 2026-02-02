from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from blog_watcher.detection.models import is_cache_fresh
from blog_watcher.detection.sitemap.detector import (
    ParsedSitemap,
    detect_sitemap_urls,
    parse_sitemap,
)
from blog_watcher.detection.urls.fingerprinter import fingerprint_urls
from blog_watcher.detection.urls.normalizer import normalize_urls
from blog_watcher.observability import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from blog_watcher.detection.http_fetcher import Fetcher
    from blog_watcher.detection.models import DetectorConfig
    from blog_watcher.storage.models import BlogState


@dataclass(frozen=True, slots=True)
class SitemapDetectionResult:
    sitemap_url: str | None
    fingerprint: str | None
    changed: bool
    ok: bool


class SitemapChangeDetector:
    def __init__(self, *, fetcher: Fetcher, config: DetectorConfig) -> None:
        self._fetcher = fetcher
        self._config = config

    async def detect(self, base_url: str, previous_state: BlogState | None) -> SitemapDetectionResult:
        if previous_state is not None and previous_state.sitemap_url and is_cache_fresh(previous_state.last_checked_at, self._config.cache_ttl_days):
            cached = await self._try_cached_sitemap(previous_state.sitemap_url, previous_state)
            if cached is not None:
                return cached

        try:
            robots_txt = await self._fetch_robots_txt(base_url)
            candidates = detect_sitemap_urls(robots_txt, base_url)
            sitemap_url, all_page_urls = await self._probe_sitemap_candidates(candidates)
        except Exception:  # noqa: BLE001
            return SitemapDetectionResult(
                sitemap_url=None,
                fingerprint=None,
                changed=False,
                ok=False,
            )

        if not all_page_urls:
            return SitemapDetectionResult(
                sitemap_url=None,
                fingerprint=None,
                changed=False,
                ok=False,
            )

        norm_config = self._config.to_normalization_config()
        normalized = normalize_urls(all_page_urls, config=norm_config)
        fingerprint = fingerprint_urls(normalized)

        changed = False
        if previous_state is not None and previous_state.url_fingerprint:
            changed = previous_state.url_fingerprint != fingerprint

        return SitemapDetectionResult(
            sitemap_url=sitemap_url,
            fingerprint=fingerprint,
            changed=changed,
            ok=True,
        )

    async def _try_cached_sitemap(self, sitemap_url: str, previous_state: BlogState | None) -> SitemapDetectionResult | None:
        parsed = await self._fetch_and_parse_sitemap(sitemap_url)
        if parsed is None:
            return None

        page_urls: list[str] = []
        if parsed.is_index:
            page_urls = await self._resolve_sitemap_index(parsed)
        else:
            page_urls = list(parsed.page_urls)

        if not page_urls:
            return None

        norm_config = self._config.to_normalization_config()
        normalized = normalize_urls(page_urls, config=norm_config)
        fingerprint = fingerprint_urls(normalized)

        changed = False
        if previous_state is not None and previous_state.url_fingerprint:
            changed = previous_state.url_fingerprint != fingerprint

        return SitemapDetectionResult(
            sitemap_url=sitemap_url,
            fingerprint=fingerprint,
            changed=changed,
            ok=True,
        )

    async def _probe_sitemap_candidates(self, candidates: list[str]) -> tuple[str | None, list[str]]:
        """Fetch and parse sitemap candidates, returning the first valid one."""
        for candidate in candidates:
            parsed = await self._fetch_and_parse_sitemap(candidate)
            if parsed is None:
                continue

            page_urls: list[str] = []
            if parsed.is_index:
                page_urls = await self._resolve_sitemap_index(parsed)
            else:
                page_urls = list(parsed.page_urls)

            return candidate, page_urls
        return None, []

    async def _fetch_and_parse_sitemap(self, url: str) -> ParsedSitemap | None:
        """Fetch a single sitemap URL and parse it."""
        try:
            result = await self._fetcher.fetch(url)
        except Exception:  # noqa: BLE001
            logger.debug("sitemap_fetch_failed", url=url)
            return None
        if result.content is None:
            return None
        return parse_sitemap(result.content, url)

    async def _resolve_sitemap_index(self, index: ParsedSitemap) -> list[str]:
        """Fetch child sitemaps from an index and collect page URLs."""
        page_urls: list[str] = []
        for child_url in index.page_urls:
            child_parsed = await self._fetch_and_parse_sitemap(child_url)
            if child_parsed is not None and not child_parsed.is_index:
                page_urls.extend(child_parsed.page_urls)
        return page_urls

    async def _fetch_robots_txt(self, base_url: str) -> str | None:
        parsed = urlparse(base_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        try:
            result = await self._fetcher.fetch(robots_url)
        except Exception:  # noqa: BLE001
            return None
        return result.content
