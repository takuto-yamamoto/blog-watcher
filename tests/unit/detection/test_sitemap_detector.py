from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st
from tests.test_utils.helpers import read_fixture

from blog_watcher.detection.sitemap.detector import (
    ParsedSitemap,
    detect_sitemap_urls,
    parse_sitemap,
)


class TestDetectSitemapUrls:
    @pytest.mark.unit
    def test_detect_sitemap_urls_from_robots_txt(self) -> None:
        robots_txt = read_fixture("sitemap/robots_with_sitemap.txt")
        urls = detect_sitemap_urls(robots_txt, "https://example.com")
        assert urls == ["https://example.com/sitemap.xml"]

    @pytest.mark.unit
    def test_detect_sitemap_urls_fallback_common_paths(self) -> None:
        urls = detect_sitemap_urls(None, "https://example.com")
        assert "https://example.com/sitemap.xml" in urls
        assert "https://example.com/sitemap_index.xml" in urls

    @pytest.mark.unit
    def test_detect_sitemap_urls_fallback_with_blog_path(self) -> None:
        urls = detect_sitemap_urls(None, "https://example.com/blog")
        assert "https://example.com/sitemap.xml" in urls
        assert "https://example.com/blog/sitemap.xml" in urls

    @pytest.mark.unit
    def test_detect_sitemap_urls_multiple_directives(self) -> None:
        robots_txt = "User-agent: *\nSitemap: https://example.com/sitemap1.xml\nSitemap: https://example.com/sitemap2.xml\n"
        urls = detect_sitemap_urls(robots_txt, "https://example.com")
        assert urls == ["https://example.com/sitemap1.xml", "https://example.com/sitemap2.xml"]


class TestParseSitemap:
    @pytest.mark.unit
    def test_parse_sitemap_urlset(self) -> None:
        content = read_fixture("sitemap/urlset.xml")
        result = parse_sitemap(content, "https://example.com/sitemap.xml")
        assert result is not None
        assert result.is_index is False
        assert len(result.page_urls) == 3
        assert "https://example.com/posts/article-1" in result.page_urls

    @pytest.mark.unit
    def test_parse_sitemap_index(self) -> None:
        content = read_fixture("sitemap/index.xml")
        result = parse_sitemap(content, "https://example.com/sitemap.xml")
        assert result is not None
        assert result.is_index is True
        assert len(result.page_urls) == 2
        assert "https://example.com/sitemap-posts.xml" in result.page_urls

    @pytest.mark.unit
    def test_parse_sitemap_no_namespace(self) -> None:
        content = read_fixture("sitemap/no_namespace.xml")
        result = parse_sitemap(content, "https://example.com/sitemap.xml")
        assert result is not None
        assert result.is_index is False
        assert len(result.page_urls) == 2

    @pytest.mark.unit
    def test_parse_sitemap_malformed_xml(self) -> None:
        result = parse_sitemap("<urlset><broken", "https://example.com/sitemap.xml")
        assert result is None

    @pytest.mark.unit
    def test_parse_sitemap_empty(self) -> None:
        content = '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>'
        result = parse_sitemap(content, "https://example.com/sitemap.xml")
        assert result is None

    @pytest.mark.unit
    @given(st.text(max_size=500))
    def test_parse_sitemap_never_crashes(self, content: str) -> None:
        result = parse_sitemap(content, "https://example.com/sitemap.xml")
        assert result is None or isinstance(result, ParsedSitemap)
