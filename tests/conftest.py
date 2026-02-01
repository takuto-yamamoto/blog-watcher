"""Shared pytest configuration for all test levels."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from hypothesis import HealthCheck, settings

from tests.test_utils.factories import FetchResultFactory
from tests.test_utils.helpers import read_fixture

if TYPE_CHECKING:
    from collections.abc import Callable

    from blog_watcher.detection.http_fetcher import FetchResult


@pytest.fixture
def feed_link_html() -> FetchResult:
    return FetchResultFactory.build(content=read_fixture("html/feed_link_rss.html"))


@pytest.fixture
def rss_valid() -> FetchResult:
    return FetchResultFactory.build(content=read_fixture("feeds/rss_valid.xml"))


@pytest.fixture
def sitemap_urlset() -> FetchResult:
    return FetchResultFactory.build(content=read_fixture("sitemap/urlset.xml"))


@pytest.fixture
def robots_allow_all() -> FetchResult:
    return FetchResultFactory.build(content="User-agent: *\nDisallow:")


@pytest.fixture
def robots_with_sitemap() -> Callable[[str], FetchResult]:
    def build(url: str) -> FetchResult:
        return FetchResultFactory.build(content=f"Sitemap: {url}")

    return build


# Configure Hypothesis global settings
settings.register_profile(
    "dev",
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
settings.register_profile(
    "ci",
    max_examples=100,
    deadline=5000,
)

if os.getenv("CI"):
    settings.load_profile("ci")
else:
    settings.load_profile("dev")


_LEVEL_MARKERS = {
    "unit": pytest.mark.unit,
    "integration": pytest.mark.integration,
    "e2e": pytest.mark.e2e,
}


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        rel = item.path.relative_to(Path(__file__).resolve().parent) if item.path else None
        if rel is None:
            continue
        for level, marker in _LEVEL_MARKERS.items():
            if rel.parts[0] == level:
                item.add_marker(marker)
                break
