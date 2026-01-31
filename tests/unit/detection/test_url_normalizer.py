from __future__ import annotations

import pytest
from hypothesis import given
from tests.strategies import url_strategy, url_with_tracking_params_strategy

from blog_watcher.detection.url_normalizer import NormalizationConfig, normalize_url, normalize_urls


@pytest.mark.unit
@pytest.mark.property_based
@given(url=url_strategy())
def test_normalize_url_is_idempotent(url: str) -> None:
    config = NormalizationConfig()

    normalized_once = normalize_url(url, config=config)
    normalized_twice = normalize_url(normalized_once, config=config)

    assert normalized_once == normalized_twice


@pytest.mark.unit
@pytest.mark.property_based
@given(url=url_strategy())
def test_normalize_url_produces_lowercase_scheme(url: str) -> None:
    config = NormalizationConfig()

    normalized = normalize_url(url, config=config)

    assert normalized.startswith(("http://", "https://"))


@pytest.mark.unit
@pytest.mark.property_based
@given(url=url_strategy())
def test_normalize_url_produces_lowercase_host(url: str) -> None:
    config = NormalizationConfig(lowercase_host=True)

    normalized = normalize_url(url, config=config)

    host = normalized.split("://", 1)[1].split("/", 1)[0]
    assert host == host.lower()


@pytest.mark.unit
@pytest.mark.property_based
@given(url=url_with_tracking_params_strategy())
def test_normalize_url_removes_tracking_parameters(url: str) -> None:
    config = NormalizationConfig(strip_tracking_params=True)

    normalized = normalize_url(url, config=config)

    tracking_params = ["utm_", "fbclid", "gclid", "mc_eid"]
    for param in tracking_params:
        assert param not in normalized


@pytest.mark.unit
@pytest.mark.property_based
@given(url=url_strategy())
def test_normalize_url_removes_fragments(url: str) -> None:
    config = NormalizationConfig(strip_fragments=True)

    normalized = normalize_url(url, config=config)

    assert "#" not in normalized


@pytest.mark.unit
@pytest.mark.parametrize(
    ("relative_url", "base_url", "expected_output"),
    [
        pytest.param(
            "../about",
            "https://example.com/blog/post",
            "https://example.com/about",
            id="parent_directory_relative",
        ),
        pytest.param(
            "./contact",
            "https://example.com/blog/",
            "https://example.com/blog/contact",
            id="current_directory_relative",
        ),
        pytest.param(
            "/absolute/path",
            "https://example.com/blog/post",
            "https://example.com/absolute/path",
            id="absolute_path",
        ),
        pytest.param(
            "page",
            "https://example.com/blog/",
            "https://example.com/blog/page",
            id="relative_without_dot",
        ),
    ],
)
def test_normalize_url_resolves_relative_urls(relative_url: str, base_url: str, expected_output: str) -> None:
    config = NormalizationConfig()

    result = normalize_url(relative_url, base_url=base_url, config=config)

    assert result == expected_output


@pytest.mark.unit
@pytest.mark.parametrize(
    ("input_url", "expected_output"),
    [
        pytest.param(
            "https://münchen.de",
            "https://xn--mnchen-3ya.de",
            id="german_umlaut",
        ),
        pytest.param(
            "https://日本.jp",
            "https://xn--wgv71a.jp",
            id="japanese_characters",
        ),
    ],
)
def test_normalize_url_converts_idn_to_punycode(input_url: str, expected_output: str) -> None:
    config = NormalizationConfig()

    result = normalize_url(input_url, config=config)

    assert result == expected_output


@pytest.mark.unit
@pytest.mark.parametrize(
    ("input_url", "expected_output"),
    [
        pytest.param(
            "https://example.com/path with spaces",
            "https://example.com/path%20with%20spaces",
            id="space_encoding",
        ),
        pytest.param(
            "https://example.com/path%20with%20spaces",
            "https://example.com/path%20with%20spaces",
            id="already_encoded_idempotent",
        ),
    ],
)
def test_normalize_url_handles_percent_encoding(input_url: str, expected_output: str) -> None:
    config = NormalizationConfig()

    result = normalize_url(input_url, config=config)

    assert result == expected_output


@pytest.mark.unit
@pytest.mark.parametrize(
    "malformed_url",
    [
        pytest.param("", id="empty"),
        pytest.param("not a url", id="no_scheme_or_host"),
        pytest.param("http://", id="no_host"),
        pytest.param("://example.com", id="missing_scheme"),
        pytest.param("http:/example.com", id="single_slash"),
    ],
)
def test_normalize_url_with_malformed_url_raises_error(malformed_url: str) -> None:
    config = NormalizationConfig()

    with pytest.raises(ValueError, match="Invalid URL"):
        normalize_url(malformed_url, config=config)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("input_url", "expected_output"),
    [
        pytest.param(
            "https://example.com/path/",
            "https://example.com/path",
            id="remove_trailing_slash",
        ),
        pytest.param(
            "https://example.com/",
            "https://example.com",
            id="root_trailing_slash",
        ),
    ],
)
def test_normalize_url_removes_trailing_slash(input_url: str, expected_output: str) -> None:
    config = NormalizationConfig(normalize_trailing_slash=True)

    result = normalize_url(input_url, config=config)

    assert result == expected_output


@pytest.mark.unit
@pytest.mark.parametrize(
    ("input_url", "expected_output"),
    [
        pytest.param(
            "http://example.com/page",
            "https://example.com/page",
            id="http_to_https",
        ),
        pytest.param(
            "https://example.com/page",
            "https://example.com/page",
            id="already_https",
        ),
    ],
)
def test_normalize_url_forces_https(input_url: str, expected_output: str) -> None:
    config = NormalizationConfig(force_https=True)

    result = normalize_url(input_url, config=config)

    assert result == expected_output


# ============================================================================
# Batch Normalization Tests
# ============================================================================


@pytest.mark.unit
def test_normalize_urls_deduplicates_identical_urls() -> None:
    urls = [
        "https://example.com/page1",
        "https://example.com/page2",
        "https://example.com/page1",  # duplicate
        "https://example.com/page3",
        "https://example.com/page2",  # duplicate
    ]
    base_url = "https://example.com"
    config = NormalizationConfig()

    result = normalize_urls(urls, base_url=base_url, config=config)

    expected_count = 3
    assert len(result) == expected_count
    assert "https://example.com/page1" in result
    assert "https://example.com/page2" in result
    assert "https://example.com/page3" in result


@pytest.mark.unit
def test_normalize_urls_with_empty_list_returns_empty_list() -> None:
    urls: list[str] = []
    base_url = "https://example.com"
    config = NormalizationConfig()

    result = normalize_urls(urls, base_url=base_url, config=config)

    assert result == []


@pytest.mark.unit
def test_normalize_url_idna_encoding_failure() -> None:
    config = NormalizationConfig()

    with pytest.raises(ValueError, match="Invalid URL"):
        normalize_url("http://\u200b.com", config=config)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("input_url", "expected_output"),
    [
        ("https://example.com/page#section?utm_source=test&valid=param", "https://example.com/page#section?valid=param"),
        ("https://example.com/page#section?utm_source=test", "https://example.com/page#section"),
        ("https://example.com/page#?utm_source=test&valid=param", "https://example.com/page#valid=param"),
        ("https://example.com/page#param1=value1&utm_source=test&param2=value2", "https://example.com/page#param1=value1&param2=value2"),
        ("https://example.com/page#param1=value1&&param2=value2", "https://example.com/page#param1=value1&param2=value2"),
    ],
)
def test_normalize_url_strip_tracking_from_fragment_variants(input_url: str, expected_output: str) -> None:
    config = NormalizationConfig(strip_tracking_params=True)

    result = normalize_url(input_url, config=config)

    assert result == expected_output


@pytest.mark.unit
def test_normalize_url_strip_fragments_empty_fragment() -> None:
    input_url = "https://example.com/page#"
    config = NormalizationConfig(strip_fragments=True)

    result = normalize_url(input_url, config=config)

    assert result == "https://example.com/page"


@pytest.mark.unit
def test_normalize_url_with_port() -> None:
    input_url = "https://example.com:8080/path"
    config = NormalizationConfig()

    result = normalize_url(input_url, config=config)

    assert result == "https://example.com:8080/path"


@pytest.mark.unit
def test_normalize_url_hostname_none_error() -> None:
    config = NormalizationConfig()

    with pytest.raises(ValueError, match="Invalid URL"):
        normalize_url("ftp://example.com", config=config)


@pytest.mark.unit
def test_normalize_url_fragment_ampersand_query_no_equals_keeps_anchor() -> None:
    input_url = "https://example.com/page#anchor&utm_source=test&param=value"
    config = NormalizationConfig(strip_tracking_params=True)

    result = normalize_url(input_url, config=config)

    assert "anchor" in result
    assert "utm_source" not in result
    assert "param=value" in result
