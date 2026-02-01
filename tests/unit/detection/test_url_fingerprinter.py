from __future__ import annotations

import re

import pytest
from hypothesis import assume, given

from blog_watcher.detection.urls.fingerprinter import fingerprint_urls, has_changed
from tests.test_utils.strategies import url_lists


@pytest.mark.pbt
@given(urls=url_lists)
def test_fingerprint_urls_is_deterministic(urls: list[str]) -> None:
    fingerprint_1 = fingerprint_urls(urls)
    fingerprint_2 = fingerprint_urls(urls)

    assert fingerprint_1 == fingerprint_2


@pytest.mark.pbt
@given(urls=url_lists)
def test_fingerprint_urls_returns_sha256_hex(urls: list[str]) -> None:
    fingerprint = fingerprint_urls(urls)

    assert re.match(r"^[0-9a-f]{64}$", fingerprint)


@pytest.mark.pbt
@given(urls_1=url_lists, urls_2=url_lists)
def test_fingerprint_urls_different_inputs_produce_different_fingerprints(
    urls_1: list[str],
    urls_2: list[str],
) -> None:
    assume(urls_1 != urls_2)

    fingerprint_1 = fingerprint_urls(urls_1)
    fingerprint_2 = fingerprint_urls(urls_2)

    assert fingerprint_1 != fingerprint_2


def test_fingerprint_urls_with_very_long_url_list() -> None:
    urls = [f"https://example.com/article-{i}" for i in range(1000)]

    fingerprint = fingerprint_urls(urls)

    assert re.match(r"^[0-9a-f]{64}$", fingerprint)


def test_fingerprint_urls_with_unicode_urls() -> None:
    urls = [
        "https://example.com/日本語",
        "https://example.com/émoji",
        "https://example.com/中文",
    ]

    fingerprint = fingerprint_urls(urls)

    assert re.match(r"^[0-9a-f]{64}$", fingerprint)


def test_has_changed_with_none_returns_true() -> None:
    """First check of a blog (no previous state)."""
    assert has_changed(None, "abc") is True


def test_has_changed_with_identical_returns_false() -> None:
    assert has_changed("abc", "abc") is False


def test_has_changed_with_different_returns_true() -> None:
    assert has_changed("abc", "xyz") is True
