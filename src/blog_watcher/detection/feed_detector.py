from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from urllib.parse import urljoin

import feedparser
from bs4 import BeautifulSoup

if TYPE_CHECKING:
    from collections.abc import Iterable


@dataclass(frozen=True, slots=True)
class FeedEntry:
    id: str
    title: str | None
    link: str | None
    published: datetime | None


@dataclass(frozen=True, slots=True)
class ParsedFeed:
    url: str
    title: str | None
    entries: tuple[FeedEntry, ...]

    Entry = FeedEntry


_COMMON_FEED_PATHS: tuple[str, ...] = (
    "/feed",
    "/rss.xml",
    "/atom.xml",
    "/rss",
    "/feed.xml",
)


def detect_feed_urls(html: str, base_url: str) -> list[str]:
    urls: list[str] = []

    soup = BeautifulSoup(html or "", "html.parser")
    for link in soup.find_all("link"):
        rel_raw = link.get("rel")
        rel: list[str] = []
        if isinstance(rel_raw, str):
            rel = [rel_raw]
        elif isinstance(rel_raw, list):
            rel = [value for value in rel_raw if isinstance(value, str)]
        rel_lower = [value.lower() for value in rel]
        if "alternate" not in rel_lower:
            continue

        href = link.get("href")
        if not href or not isinstance(href, str):
            continue

        link_type = link.get("type")
        if link_type and isinstance(link_type, str):
            link_type_lower = link_type.lower()
            if "rss+xml" not in link_type_lower and "atom+xml" not in link_type_lower and "xml" not in link_type_lower:
                continue

        urls.append(urljoin(base_url, href))

    if not urls:
        urls.extend(urljoin(base_url, path) for path in _COMMON_FEED_PATHS)

    return _dedupe(urls)


def parse_feed(content: str, feed_url: str) -> ParsedFeed | None:
    parsed = feedparser.parse(content or "")

    feed_title = getattr(parsed.feed, "title", None) if hasattr(parsed, "feed") else None
    if not feed_title:
        feed_title = None

    if parsed.bozo and not parsed.entries and feed_title is None:
        return None

    entries: list[FeedEntry] = []
    for index, entry in enumerate(parsed.entries or []):
        entry_id = _entry_id(entry, index=index)
        entry_title = _get_str(entry, "title")
        entry_link = _get_str(entry, "link")
        published = _parse_published(entry)
        entries.append(FeedEntry(id=entry_id, title=entry_title, link=entry_link, published=published))

    return ParsedFeed(url=feed_url, title=feed_title, entries=tuple(entries))


def _entry_id(entry: object, *, index: int) -> str:
    guid = _get_str(entry, "id") or _get_str(entry, "guid")
    if guid:
        return guid

    link = _get_str(entry, "link")
    if link:
        return link

    title = _get_str(entry, "title")
    published = _parse_published(entry)
    if title and published is not None:
        return f"{title}|{published.isoformat()}"

    published_text = _get_str(entry, "published")
    if title and published_text:
        return f"{title}|{published_text}"

    if title:
        return title

    return f"entry-{index}"


def _parse_published(entry: object) -> datetime | None:
    parsed: object | None
    if isinstance(entry, dict):
        if "published_parsed" in entry:
            parsed = entry.get("published_parsed")
        elif "updated_parsed" in entry:
            parsed = entry.get("updated_parsed")
        else:
            parsed = None
    else:
        parsed = getattr(entry, "published_parsed", None)
        if parsed is None:
            parsed = getattr(entry, "updated_parsed", None)
    if not isinstance(parsed, time.struct_time):
        return None
    try:
        year, month, day, hour, minute, second = parsed[:6]
        return datetime(year, month, day, hour, minute, second, tzinfo=UTC)
    except (TypeError, ValueError, OverflowError):
        return None


def _get_str(obj: object, name: str) -> str | None:
    value = getattr(obj, name, None)
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def _dedupe(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        output.append(item)
    return output
