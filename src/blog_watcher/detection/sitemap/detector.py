"""Sitemap discovery and parsing utilities."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from collections.abc import Iterable

_SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
_SITEMAP_DIRECTIVE_RE = re.compile(r"^Sitemap:\s*(.+)$", re.IGNORECASE | re.MULTILINE)


@dataclass(frozen=True, slots=True)
class ParsedSitemap:
    url: str
    page_urls: tuple[str, ...]
    is_index: bool


def detect_sitemap_urls(robots_txt: str | None, base_url: str) -> list[str]:
    """Extract sitemap URLs from robots.txt or fall back to common paths."""
    urls: list[str] = []

    if robots_txt:
        for match in _SITEMAP_DIRECTIVE_RE.finditer(robots_txt):
            url = match.group(1).strip()
            if url:
                urls.append(url)

    if urls:
        return _dedupe(urls)

    parsed = urlparse(base_url)
    domain_root = f"{parsed.scheme}://{parsed.netloc}"

    candidates = [
        f"{domain_root}/sitemap.xml",
        f"{domain_root}/sitemap_index.xml",
    ]

    path = parsed.path.rstrip("/")
    if path and path != "/":
        candidates.append(f"{domain_root}{path}/sitemap.xml")

    return _dedupe(candidates)


def parse_sitemap(content: str, sitemap_url: str) -> ParsedSitemap | None:
    """Parse a sitemap XML document, returning page URLs or child sitemap URLs."""
    try:
        root = ET.fromstring(content)  # noqa: S314
    except ET.ParseError:
        return None

    tag = _strip_ns(root.tag)

    if tag == "urlset":
        locs = _find_locs(root, "url")
        if not locs:
            return None
        return ParsedSitemap(url=sitemap_url, page_urls=tuple(locs), is_index=False)

    if tag == "sitemapindex":
        locs = _find_locs(root, "sitemap")
        if not locs:
            return None
        return ParsedSitemap(url=sitemap_url, page_urls=tuple(locs), is_index=True)

    return None


def _find_locs(root: ET.Element, child_tag: str) -> list[str]:
    """Find <loc> elements inside child elements, trying with and without namespace."""
    locs: list[str] = []

    # Try with namespace first
    for elem in root.findall(f"{{{_SITEMAP_NS}}}{child_tag}"):
        loc = elem.findtext(f"{{{_SITEMAP_NS}}}loc")
        if loc and loc.strip():
            locs.append(loc.strip())

    if locs:
        return locs

    # Retry without namespace
    for elem in root.findall(child_tag):
        loc = elem.findtext("loc")
        if loc and loc.strip():
            locs.append(loc.strip())

    return locs


def _strip_ns(tag: str) -> str:
    if tag.startswith("{"):
        return tag.split("}", 1)[1]
    return tag


def _dedupe(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        output.append(item)
    return output
