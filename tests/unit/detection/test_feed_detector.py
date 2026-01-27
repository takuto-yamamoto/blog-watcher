from __future__ import annotations

from datetime import UTC, datetime

import pytest
from blog_watcher.detection.feed_detector import (
    FeedEntry,
    ParsedFeed,
    detect_feed_urls,
    parse_feed,
)
from hypothesis import given
from hypothesis import strategies as st

# ============================================================================
# Hypothesis Strategies for Property-Based Testing
# ============================================================================


@st.composite
def xml_strategy(draw: st.DrawFn) -> str:
    """Generate arbitrary XML-like content for crash resistance testing."""
    tags = draw(
        st.lists(
            st.sampled_from(
                [
                    "<rss>",
                    "</rss>",
                    "<channel>",
                    "</channel>",
                    "<item>",
                    "</item>",
                    "text",
                    "<![CDATA[content]]>",
                ]
            ),
            max_size=30,
        )
    )
    return "".join(tags)


@st.composite
def html_with_links_strategy(draw: st.DrawFn) -> str:
    """Generate HTML with potentially malformed link tags."""
    return draw(st.text(min_size=0, max_size=500))


# ============================================================================
# Property-Based Tests (20% of test coverage)
# ============================================================================


@pytest.mark.unit
@pytest.mark.property_based
@given(content=xml_strategy())
def test_parse_feed_never_crashes_on_arbitrary_input(content: str) -> None:
    """Test that parse_feed never crashes on arbitrary XML input.

    This is a crash resistance test - should handle malformed XML gracefully.
    """
    try:
        result = parse_feed(content, feed_url="https://example.com/feed")
        # Should return None for invalid feeds or ParsedFeed for valid ones
        assert result is None or isinstance(result, ParsedFeed)
    except Exception as e:
        # Should not raise unexpected exceptions
        pytest.fail(f"parse_feed crashed with: {e}")


@pytest.mark.unit
@pytest.mark.property_based
@given(html=html_with_links_strategy())
def test_detect_feed_urls_never_crashes_on_arbitrary_html(html: str) -> None:
    """Test that detect_feed_urls never crashes on arbitrary HTML input."""
    try:
        result = detect_feed_urls(html, base_url="https://example.com")
        assert isinstance(result, list)
        assert all(isinstance(url, str) for url in result)
    except Exception as e:
        pytest.fail(f"detect_feed_urls crashed with: {e}")


@pytest.mark.unit
@pytest.mark.property_based
@given(content=xml_strategy())
def test_parsed_feed_entries_have_non_empty_ids(content: str) -> None:
    """Test that all parsed feed entries have non-empty IDs.

    This is a critical invariant - every entry must have a unique identifier.
    """
    result = parse_feed(content, feed_url="https://example.com/feed")

    if result is not None:
        for entry in result.entries:
            assert entry.id, f"Entry ID should never be empty: {entry}"
            assert len(entry.id) > 0


# ============================================================================
# Example-Based Tests (80% of test coverage)
# ============================================================================


@pytest.mark.unit
def test_detect_feed_urls_from_rss_link_tag() -> None:
    """Test detection of RSS feed from <link rel='alternate'> tag."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <link rel="alternate" type="application/rss+xml" href="/feed.xml">
    </head>
    </html>
    """
    base_url = "https://example.com"

    result = detect_feed_urls(html, base_url=base_url)

    assert len(result) > 0
    assert any("feed.xml" in url for url in result)


@pytest.mark.unit
def test_detect_feed_urls_from_atom_link_tag() -> None:
    """Test detection of Atom feed from <link rel='alternate'> tag."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <link rel="alternate" type="application/atom+xml" href="/atom.xml">
    </head>
    </html>
    """
    base_url = "https://example.com"

    result = detect_feed_urls(html, base_url=base_url)

    assert len(result) > 0
    assert any("atom.xml" in url for url in result)


@pytest.mark.unit
def test_detect_feed_urls_fallback_to_common_paths() -> None:
    """Test fallback to common feed paths when no link tags found."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Blog without feed links</title>
    </head>
    </html>
    """
    base_url = "https://example.com"

    result = detect_feed_urls(html, base_url=base_url)

    # Should return common feed paths as candidates
    assert isinstance(result, list)
    # Common paths include /feed, /rss.xml, /atom.xml, etc.
    common_paths = ["/feed", "/rss.xml", "/atom.xml", "/rss", "/feed.xml"]
    assert any(any(path in url for path in common_paths) for url in result)


@pytest.mark.unit
def test_detect_feed_urls_with_multiple_feeds() -> None:
    """Test detection of multiple feed URLs."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <link rel="alternate" type="application/rss+xml" href="/feed.xml" title="Main Feed">
        <link rel="alternate" type="application/atom+xml" href="/atom.xml" title="Atom Feed">
    </head>
    </html>
    """
    base_url = "https://example.com"

    result = detect_feed_urls(html, base_url=base_url)

    assert len(result) >= 2
    assert any("feed.xml" in url for url in result)
    assert any("atom.xml" in url for url in result)


@pytest.mark.unit
def test_parse_feed_with_valid_rss() -> None:
    """Test parsing of valid RSS 2.0 feed."""
    rss_content = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <title>Example Blog</title>
            <link>https://example.com</link>
            <description>A sample blog</description>
            <item>
                <title>Article 1</title>
                <link>https://example.com/article-1</link>
                <guid>article-1-guid</guid>
                <pubDate>Mon, 01 Jan 2024 10:00:00 GMT</pubDate>
            </item>
            <item>
                <title>Article 2</title>
                <link>https://example.com/article-2</link>
                <guid>article-2-guid</guid>
                <pubDate>Tue, 02 Jan 2024 10:00:00 GMT</pubDate>
            </item>
        </channel>
    </rss>
    """
    feed_url = "https://example.com/feed.xml"

    result = parse_feed(rss_content, feed_url=feed_url)

    assert result is not None
    assert result.url == feed_url
    assert result.title == "Example Blog"
    assert len(result.entries) == 2

    # Check first entry
    entry1 = result.entries[0]
    assert entry1.id == "article-1-guid"
    assert entry1.title == "Article 1"
    assert entry1.link == "https://example.com/article-1"
    assert isinstance(entry1.published, datetime)


@pytest.mark.unit
def test_parse_feed_with_valid_atom() -> None:
    """Test parsing of valid Atom 1.0 feed."""
    atom_content = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
        <title>Example Blog</title>
        <link href="https://example.com"/>
        <updated>2024-01-02T10:00:00Z</updated>
        <entry>
            <title>Article 1</title>
            <link href="https://example.com/article-1"/>
            <id>urn:uuid:article-1-id</id>
            <updated>2024-01-01T10:00:00Z</updated>
        </entry>
        <entry>
            <title>Article 2</title>
            <link href="https://example.com/article-2"/>
            <id>urn:uuid:article-2-id</id>
            <updated>2024-01-02T10:00:00Z</updated>
        </entry>
    </feed>
    """
    feed_url = "https://example.com/atom.xml"

    result = parse_feed(atom_content, feed_url=feed_url)

    assert result is not None
    assert result.url == feed_url
    assert result.title == "Example Blog"
    assert len(result.entries) == 2

    # Check first entry
    entry1 = result.entries[0]
    assert entry1.id == "urn:uuid:article-1-id"
    assert entry1.title == "Article 1"
    assert entry1.link == "https://example.com/article-1"


@pytest.mark.unit
def test_parse_feed_entry_id_priority_guid_over_link() -> None:
    """Test that entry ID prioritizes guid over link."""
    rss_content = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <title>Blog</title>
            <item>
                <title>Article</title>
                <link>https://example.com/article</link>
                <guid>unique-guid-123</guid>
            </item>
        </channel>
    </rss>
    """
    feed_url = "https://example.com/feed.xml"

    result = parse_feed(rss_content, feed_url=feed_url)

    assert result is not None
    assert len(result.entries) == 1
    assert result.entries[0].id == "unique-guid-123"


@pytest.mark.unit
def test_parse_feed_entry_id_fallback_to_link() -> None:
    """Test that entry ID falls back to link when guid is missing."""
    rss_content = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <title>Blog</title>
            <item>
                <title>Article</title>
                <link>https://example.com/article</link>
            </item>
        </channel>
    </rss>
    """
    feed_url = "https://example.com/feed.xml"

    result = parse_feed(rss_content, feed_url=feed_url)

    assert result is not None
    assert len(result.entries) == 1
    assert result.entries[0].id == "https://example.com/article"


@pytest.mark.unit
def test_parse_feed_entry_id_fallback_to_title_plus_published() -> None:
    """Test that entry ID falls back to title+published when guid and link missing."""
    rss_content = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <title>Blog</title>
            <item>
                <title>Article Title</title>
                <pubDate>Mon, 01 Jan 2024 10:00:00 GMT</pubDate>
            </item>
        </channel>
    </rss>
    """
    feed_url = "https://example.com/feed.xml"

    result = parse_feed(rss_content, feed_url=feed_url)

    assert result is not None
    assert len(result.entries) == 1
    # ID should be combination of title and published date
    assert "Article Title" in result.entries[0].id
    assert result.entries[0].id  # Should not be empty


@pytest.mark.unit
def test_parse_feed_with_malformed_xml_returns_none() -> None:
    """Test that malformed XML returns None instead of crashing."""
    malformed_xml = """<?xml version="1.0"?>
    <rss version="2.0">
        <channel>
            <title>Unclosed Title
            <item>
                <title>Article</title>
    """
    feed_url = "https://example.com/feed.xml"

    result = parse_feed(malformed_xml, feed_url=feed_url)

    assert result is None


@pytest.mark.unit
def test_parse_feed_with_empty_content_returns_none() -> None:
    """Test that empty content returns None."""
    feed_url = "https://example.com/feed.xml"

    result = parse_feed("", feed_url=feed_url)

    assert result is None


@pytest.mark.unit
def test_parse_feed_with_no_items_returns_empty_entries() -> None:
    """Test that feed with no items returns empty entries tuple."""
    rss_content = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <title>Empty Blog</title>
            <link>https://example.com</link>
        </channel>
    </rss>
    """
    feed_url = "https://example.com/feed.xml"

    result = parse_feed(rss_content, feed_url=feed_url)

    assert result is not None
    assert len(result.entries) == 0


@pytest.mark.unit
def test_parse_feed_with_invalid_date_handles_gracefully() -> None:
    """Test that invalid pubDate is handled gracefully."""
    rss_content = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <title>Blog</title>
            <item>
                <title>Article</title>
                <link>https://example.com/article</link>
                <guid>article-guid</guid>
                <pubDate>Invalid Date Format</pubDate>
            </item>
        </channel>
    </rss>
    """
    feed_url = "https://example.com/feed.xml"

    result = parse_feed(rss_content, feed_url=feed_url)

    assert result is not None
    assert len(result.entries) == 1
    # Published should be None for invalid date
    assert result.entries[0].published is None


@pytest.mark.unit
def test_parse_feed_handles_cdata_sections() -> None:
    """Test that CDATA sections in titles/content are parsed correctly."""
    rss_content = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <title><![CDATA[Blog with <special> characters]]></title>
            <item>
                <title><![CDATA[Article with & symbols]]></title>
                <link>https://example.com/article</link>
                <guid>article-guid</guid>
            </item>
        </channel>
    </rss>
    """
    feed_url = "https://example.com/feed.xml"

    result = parse_feed(rss_content, feed_url=feed_url)

    assert result is not None
    assert "special" in result.title or "Blog" in result.title
    assert "&" in result.entries[0].title or "Article" in result.entries[0].title


@pytest.mark.unit
def test_parse_feed_with_relative_urls_in_links() -> None:
    """Test that relative URLs in feed entries are handled."""
    rss_content = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <title>Blog</title>
            <item>
                <title>Article</title>
                <link>/article-1</link>
                <guid>article-1</guid>
            </item>
        </channel>
    </rss>
    """
    feed_url = "https://example.com/feed.xml"

    result = parse_feed(rss_content, feed_url=feed_url)

    assert result is not None
    assert len(result.entries) == 1
    # Link should be present (normalization is separate concern)
    assert result.entries[0].link == "/article-1"


@pytest.mark.unit
def test_parse_feed_with_missing_title() -> None:
    """Test that missing feed title is handled gracefully."""
    rss_content = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <link>https://example.com</link>
            <item>
                <title>Article</title>
                <guid>article-guid</guid>
            </item>
        </channel>
    </rss>
    """
    feed_url = "https://example.com/feed.xml"

    result = parse_feed(rss_content, feed_url=feed_url)

    assert result is not None
    assert result.title is None or result.title == ""


@pytest.mark.unit
def test_parse_feed_preserves_entry_order() -> None:
    """Test that feed entries are returned in document order."""
    rss_content = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <title>Blog</title>
            <item>
                <title>First</title>
                <guid>first</guid>
            </item>
            <item>
                <title>Second</title>
                <guid>second</guid>
            </item>
            <item>
                <title>Third</title>
                <guid>third</guid>
            </item>
        </channel>
    </rss>
    """
    feed_url = "https://example.com/feed.xml"

    result = parse_feed(rss_content, feed_url=feed_url)

    assert result is not None
    assert len(result.entries) == 3
    assert result.entries[0].id == "first"
    assert result.entries[1].id == "second"
    assert result.entries[2].id == "third"


@pytest.mark.unit
def test_detect_feed_urls_with_empty_html_returns_fallback_paths() -> None:
    """Test that empty HTML returns fallback feed paths."""
    html = ""
    base_url = "https://example.com"

    result = detect_feed_urls(html, base_url=base_url)

    # Should return common feed paths
    assert isinstance(result, list)
    assert len(result) > 0


@pytest.mark.unit
def test_detect_feed_urls_resolves_relative_paths() -> None:
    """Test that relative feed URLs are resolved against base_url."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <link rel="alternate" type="application/rss+xml" href="/feed.xml">
    </head>
    </html>
    """
    base_url = "https://example.com/blog"

    result = detect_feed_urls(html, base_url=base_url)

    assert len(result) > 0
    # Should contain absolute URL
    assert any(url.startswith("http") for url in result)


@pytest.mark.unit
def test_feed_entry_dataclass_immutability() -> None:
    """Test that FeedEntry is frozen (immutable)."""
    entry = FeedEntry(
        id="test-id",
        title="Test Title",
        link="https://example.com/article",
        published=datetime.now(tz=UTC),
    )

    with pytest.raises(AttributeError):
        entry.id = "new-id"  # type: ignore[misc]


@pytest.mark.unit
def test_parsed_feed_dataclass_immutability() -> None:
    """Test that ParsedFeed is frozen (immutable)."""
    feed = ParsedFeed(
        url="https://example.com/feed.xml",
        title="Test Feed",
        entries=(),
    )

    with pytest.raises(AttributeError):
        feed.title = "New Title"  # type: ignore[misc]


@pytest.mark.unit
def test_feed_entry_with_none_optional_fields() -> None:
    """Test that FeedEntry accepts None for optional fields."""
    entry = FeedEntry(
        id="test-id",
        title=None,
        link=None,
        published=None,
    )

    assert entry.id == "test-id"
    assert entry.title is None
    assert entry.link is None
    assert entry.published is None
