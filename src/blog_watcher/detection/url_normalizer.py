"""URL normalization utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import parse_qsl, quote, urlencode, urljoin, urlparse, urlunparse

if TYPE_CHECKING:
    from collections.abc import Iterable
    from urllib.parse import ParseResult


@dataclass(frozen=True, slots=True)
class NormalizationConfig:
    lowercase_host: bool = False
    strip_tracking_params: bool = False
    strip_fragments: bool = False
    normalize_trailing_slash: bool = False
    force_https: bool = False


_INVALID_URL = "Invalid URL"


def normalize_url(url: str, *, base_url: str | None = None, config: NormalizationConfig | None = None) -> str:
    if not url:
        raise ValueError(_INVALID_URL)

    config = config or NormalizationConfig()
    parsed, scheme = _parse_url(url, base_url=base_url)

    netloc = _build_netloc(parsed, lowercase_host=config.lowercase_host)
    path = _normalize_path(parsed.path, normalize_trailing_slash=config.normalize_trailing_slash)

    query = parsed.query
    fragment = parsed.fragment
    if config.strip_tracking_params:
        query = _strip_tracking_params(query)
        fragment = _strip_tracking_from_fragment(fragment)

    if config.strip_fragments:
        fragment = ""

    output_scheme = "https" if config.force_https else scheme
    return urlunparse((output_scheme, netloc, path, "", query, fragment))


def normalize_urls(urls: Iterable[str], *, base_url: str | None = None, config: NormalizationConfig | None = None) -> list[str]:
    config = config or NormalizationConfig()
    seen: set[str] = set()
    normalized_urls: list[str] = []

    for url in urls:
        normalized = normalize_url(url, base_url=base_url, config=config)
        if normalized in seen:
            continue
        seen.add(normalized)
        normalized_urls.append(normalized)

    return normalized_urls


def _parse_url(url: str, *, base_url: str | None) -> tuple[ParseResult, str]:
    resolved = urljoin(base_url, url) if base_url is not None else url
    parsed = urlparse(resolved)
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(_INVALID_URL)
    if parsed.hostname is None:
        raise ValueError(_INVALID_URL)
    return parsed, scheme


def _build_netloc(parsed: ParseResult, *, lowercase_host: bool) -> str:
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError(_INVALID_URL)
    try:
        host_idna = hostname.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise ValueError(_INVALID_URL) from exc
    if lowercase_host:
        host_idna = host_idna.lower()

    userinfo = ""
    if parsed.username is not None:
        userinfo = parsed.username
        if parsed.password is not None:
            userinfo = f"{userinfo}:{parsed.password}"
        userinfo = f"{userinfo}@"

    netloc = f"{userinfo}{host_idna}"
    if parsed.port is not None:
        netloc = f"{netloc}:{parsed.port}"
    return netloc


def _normalize_path(path: str, *, normalize_trailing_slash: bool) -> str:
    if normalize_trailing_slash:
        if path == "/":
            path = ""
        elif path.endswith("/"):
            path = path[:-1]
    return quote(path or "", safe="/%")


def _strip_tracking_params(query: str) -> str:
    if not query:
        return ""
    params = parse_qsl(query, keep_blank_values=True)
    filtered = [(key, value) for key, value in params if not _is_tracking_param(key)]
    return urlencode(filtered, doseq=True)


def _strip_tracking_from_fragment(fragment: str) -> str:
    if "?" in fragment:
        prefix, query = fragment.split("?", 1)
        cleaned = _strip_tracking_from_ampersand_query(query)
        if not cleaned:
            return prefix
        if not prefix:
            return cleaned
        return f"{prefix}?{cleaned}"
    if "&" in fragment:
        return _strip_tracking_from_ampersand_query(fragment)
    return fragment


def _strip_tracking_from_ampersand_query(query: str) -> str:
    if not query:
        return ""
    parts = query.split("&")
    kept: list[str] = []
    for part in parts:
        if not part:
            continue
        if "=" not in part:
            kept.append(part)
            continue
        key = part.split("=", 1)[0]
        if _is_tracking_param(key):
            continue
        kept.append(part)
    return "&".join(kept)


def _is_tracking_param(key: str) -> bool:
    lowered = key.lower()
    return lowered.startswith("utm_") or lowered in {"fbclid", "gclid", "mc_eid"}
