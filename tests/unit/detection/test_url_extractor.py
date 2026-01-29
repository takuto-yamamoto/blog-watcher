from __future__ import annotations

import pytest
from hypothesis import given
from tests.factories import HtmlFactory
from tests.strategies import html_strategy, random_html

from blog_watcher.detection.url_extractor import ExtractionConfig, extract_urls


@pytest.mark.unit
@pytest.mark.property_based
@given(html=html_strategy())
def test_extract_urls_never_crashes_on_arbitrary_html(html: str) -> None:
    config = ExtractionConfig(selector="a")

    result = extract_urls(html, config=config)

    assert all(isinstance(url, str) for url in result)


@pytest.mark.unit
@pytest.mark.property_based
@given(html=random_html)
def test_extract_urls_nonmatching_selector_returns_empty(html: str) -> None:
    config = ExtractionConfig(selector="nonexistenttag")

    result = extract_urls(html, config=config)

    assert result == []


@pytest.mark.unit
def test_extract_urls_with_valid_selector() -> None:
    config = ExtractionConfig(selector="article a")

    result = extract_urls(HtmlFactory.build(), config=config)

    assert "/posts/article-1" in result
    assert "/posts/article-2" in result


@pytest.mark.unit
def test_extract_urls_with_exclude_selectors() -> None:
    config = ExtractionConfig(
        selector="a",
        exclude_selectors=("nav a", "footer a"),
    )

    result = extract_urls(HtmlFactory.build(), config=config)

    assert "/about" not in result
    assert "/contact" not in result
    assert "/privacy" not in result
    assert "/posts/article-1" in result
    assert "/posts/article-2" in result


@pytest.mark.unit
@pytest.mark.parametrize(
    "invalid_selector",
    [
        pytest.param("", id="empty_selector"),
        pytest.param("a[href=unclosed", id="malformed_attribute_selector"),
        pytest.param("::invalid", id="invalid_pseudo_element"),
    ],
)
def test_extract_urls_with_invalid_selector_raises_error(invalid_selector: str) -> None:
    config = ExtractionConfig(selector=invalid_selector)
    html = "<a href='/link'>Link</a>"

    with pytest.raises(ValueError, match="selector"):
        extract_urls(html, config=config)


@pytest.mark.unit
def test_extract_urls_with_custom_attribute() -> None:
    html = """
    <img src="/image1.jpg" alt="Image 1">
    <img src="/image2.jpg" alt="Image 2">
    """
    config = ExtractionConfig(selector="img", attribute="src")

    result = extract_urls(html, config=config)

    assert "/image1.jpg" in result
    assert "/image2.jpg" in result


@pytest.mark.unit
def test_extract_urls_with_missing_attribute_excludes_element() -> None:
    html = """
    <a href="/link1">Link 1</a>
    <a>Link 2 (no href)</a>
    <a href="/link3">Link 3</a>
    """
    config = ExtractionConfig(selector="a", attribute="href")

    result = extract_urls(html, config=config)

    assert len(result) == 2
    assert "/link1" in result
    assert "/link3" in result
