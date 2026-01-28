from __future__ import annotations

from datetime import datetime

import pytest
from hypothesis import given
from tests.conftest import read_fixture
from tests.strategies import html_with_links_strategy, xml_strategy

from blog_watcher.detection.feed_detector import (
    ParsedFeed,
    detect_feed_urls,
    parse_feed,
)


@pytest.mark.unit
@pytest.mark.property_based
@given(content=xml_strategy())
def test_parse_feed_never_crashes_on_arbitrary_input(content: str) -> None:
    result = parse_feed(content, feed_url="https://example.com/feed")

    assert result is None or isinstance(result, ParsedFeed)


@pytest.mark.unit
@pytest.mark.property_based
@given(html=html_with_links_strategy())
def test_detect_feed_urls_never_crashes_on_arbitrary_html(html: str) -> None:
    result = detect_feed_urls(html, base_url="https://example.com")

    assert all(isinstance(url, str) for url in result)


@pytest.mark.unit
@pytest.mark.property_based
@given(content=xml_strategy())
def test_parsed_feed_entries_have_non_empty_ids(content: str) -> None:
    result = parse_feed(content, feed_url="https://example.com/feed")

    if result is not None:
        for entry in result.entries:
            assert entry.id, f"Entry ID should never be empty: {entry}"


@pytest.mark.unit
def test_detect_feed_urls_includes_link_rel_alternate_rss() -> None:
    html = read_fixture("html/feed_link_rss.html")

    result = detect_feed_urls(html, base_url="https://example.com")

    assert "https://example.com/feed.xml" in result


@pytest.mark.unit
def test_detect_feed_urls_includes_link_rel_alternate_atom() -> None:
    html = read_fixture("html/feed_link_atom.html")

    result = detect_feed_urls(html, base_url="https://example.com")

    assert "https://example.com/atom.xml" in result


@pytest.mark.unit
def test_detect_feed_urls_includes_both_rss_and_atom_links() -> None:
    html = read_fixture("html/feed_links_both.html")

    result = detect_feed_urls(html, base_url="https://example.com")

    assert "https://example.com/feed.xml" in result
    assert "https://example.com/atom.xml" in result


@pytest.mark.unit
def test_detect_feed_urls_falls_back_to_common_paths_when_no_links() -> None:
    html = read_fixture("html/no_feed_links.html")

    result = detect_feed_urls(html, base_url="https://example.com")

    assert "https://example.com/feed" in result
    assert "https://example.com/rss.xml" in result
    assert "https://example.com/atom.xml" in result
    assert "https://example.com/rss" in result
    assert "https://example.com/feed.xml" in result


@pytest.mark.unit
def test_detect_feed_urls_resolves_relative_urls_with_base_url() -> None:
    html = read_fixture("html/feed_link_rss.html")

    result = detect_feed_urls(html, base_url="https://example.com/blog")

    assert "https://example.com/feed.xml" in result


@pytest.mark.unit
def test_parse_feed_with_valid_rss() -> None:
    rss_content = read_fixture("feeds/rss_valid.xml")
    feed_url = "https://example.com/feed.xml"

    result = parse_feed(rss_content, feed_url=feed_url)

    assert result is not None
    assert result.url == feed_url
    assert result.title == "Example Blog"

    expected_count = 2
    assert len(result.entries) == expected_count

    entry1 = result.entries[0]
    assert entry1.id == "article-1-guid"
    assert entry1.title == "Article 1"
    assert entry1.link == "https://example.com/article-1"
    assert isinstance(entry1.published, datetime)


@pytest.mark.unit
def test_parse_feed_with_valid_atom() -> None:
    atom_content = read_fixture("feeds/atom_valid.xml")
    feed_url = "https://example.com/atom.xml"

    result = parse_feed(atom_content, feed_url=feed_url)

    assert result is not None
    assert result.url == feed_url
    assert result.title == "Example Blog"

    expected_count = 2
    assert len(result.entries) == expected_count

    entry1 = result.entries[0]
    assert entry1.id == "urn:uuid:article-1-id"
    assert entry1.title == "Article 1"
    assert entry1.link == "https://example.com/article-1"


@pytest.mark.unit
@pytest.mark.parametrize(
    ("fixture_name", "expected_id"),
    [
        pytest.param(
            "feeds/rss_guid.xml",
            "unique-guid-123",
            id="guid_preferred_over_link",
        ),
        pytest.param(
            "feeds/rss_no_guid.xml",
            "https://example.com/article",
            id="link_used_when_guid_missing",
        ),
    ],
)
def test_parse_feed_entry_id_priority_and_fallback(
    fixture_name: str,
    expected_id: str,
) -> None:
    rss_content = read_fixture(fixture_name)
    feed_url = "https://example.com/feed.xml"

    result = parse_feed(rss_content, feed_url=feed_url)

    assert result is not None
    assert len(result.entries) == 1
    assert result.entries[0].id == expected_id


@pytest.mark.unit
def test_parse_feed_entry_id_fallback_to_title_plus_published() -> None:
    rss_content = read_fixture("feeds/rss_title_published_only.xml")
    feed_url = "https://example.com/feed.xml"

    result = parse_feed(rss_content, feed_url=feed_url)

    assert result is not None
    assert len(result.entries) == 1
    assert "Article Title" in result.entries[0].id


@pytest.mark.unit
def test_parse_feed_with_no_items_returns_empty_entries() -> None:
    rss_content = read_fixture("feeds/rss_no_items.xml")
    feed_url = "https://example.com/feed.xml"

    result = parse_feed(rss_content, feed_url=feed_url)

    assert result is not None
    assert len(result.entries) == 0


@pytest.mark.unit
def test_parse_feed_with_invalid_date_handles_gracefully() -> None:
    rss_content = read_fixture("feeds/rss_invalid_date.xml")
    feed_url = "https://example.com/feed.xml"

    result = parse_feed(rss_content, feed_url=feed_url)

    assert result is not None
    assert len(result.entries) == 1
    assert result.entries[0].published is None


@pytest.mark.unit
def test_parse_feed_decodes_cdata_sections_when_valid() -> None:
    rss_content = read_fixture("feeds/rss_cdata_valid.xml")
    feed_url = "https://example.com/feed.xml"

    result = parse_feed(rss_content, feed_url=feed_url)

    assert result is not None
    assert result.title == "Blog with <special> characters"
    assert result.entries[0].title == "Article with & symbols"


@pytest.mark.unit
def test_parse_feed_handles_malformed_cdata_gracefully() -> None:
    rss_content = read_fixture("feeds/rss_cdata_malformed.xml")
    feed_url = "https://example.com/feed.xml"

    result = parse_feed(rss_content, feed_url=feed_url)

    assert result is None or isinstance(result, ParsedFeed)


@pytest.mark.unit
def test_parse_feed_with_missing_title() -> None:
    rss_content = read_fixture("feeds/rss_missing_title.xml")
    feed_url = "https://example.com/feed.xml"

    result = parse_feed(rss_content, feed_url=feed_url)

    assert result is not None
    assert result.title is None


@pytest.mark.unit
def test_parse_feed_preserves_entry_order() -> None:
    rss_content = read_fixture("feeds/rss_preserve_order.xml")
    feed_url = "https://example.com/feed.xml"

    result = parse_feed(rss_content, feed_url=feed_url)

    expected_count = 3
    assert result is not None
    assert len(result.entries) == expected_count

    assert result.entries[0].id == "first"
    assert result.entries[1].id == "second"
    assert result.entries[2].id == "third"
