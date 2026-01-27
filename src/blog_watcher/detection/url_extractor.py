from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup
from soupsieve import SelectorSyntaxError

if TYPE_CHECKING:
    from bs4 import Tag


@dataclass(frozen=True, slots=True)
class ExtractionConfig:
    selector: str
    attribute: str = "href"
    exclude_selectors: tuple[str, ...] = ()


def extract_urls(html: str, *, config: ExtractionConfig) -> list[str]:
    _invalid_selector_msg = "selector cannot be empty"
    if not config.selector:
        raise ValueError(_invalid_selector_msg)

    soup = _parse_html(html)

    exclude_set: set[Tag] = set()
    for exclude_selector in config.exclude_selectors:
        # Invalid exclude selectors are silently ignored
        with suppress(SelectorSyntaxError, NotImplementedError):
            exclude_set.update(soup.select(exclude_selector))

    try:
        elements = soup.select(config.selector)
    except (SelectorSyntaxError, NotImplementedError) as exc:
        _invalid_selector_err = f"Invalid selector: {config.selector}"
        raise ValueError(_invalid_selector_err) from exc

    urls: list[str] = []
    for element in elements:
        if element in exclude_set:
            continue
        url = element.get(config.attribute)
        if url is not None and isinstance(url, str):
            urls.append(url)

    return urls


def _parse_html(html: str) -> BeautifulSoup:
    """
    Parse HTML with fallback parser strategy.

    Tries lxml first for speed, falls back to html5lib for robustness.
    """
    try:
        return BeautifulSoup(html, "lxml")
    except Exception:  # noqa: BLE001 - Fallback to html5lib on any lxml parser failure
        return BeautifulSoup(html, "html5lib")
