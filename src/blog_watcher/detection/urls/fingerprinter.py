"""URL fingerprinting utilities for detecting changes in URL collections."""

from __future__ import annotations

import hashlib


def fingerprint_urls(urls: list[str]) -> str:
    content = "\n".join(urls)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def has_changed(old: str | None, new: str) -> bool:
    if old is None:
        return True
    return old != new
