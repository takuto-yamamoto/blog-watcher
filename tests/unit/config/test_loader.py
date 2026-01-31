from pathlib import Path

import pytest
from pydantic import ValidationError
from tests.conftest import fixture_path

from blog_watcher.config import ConfigError, load_config


def _load_validation_error(path: Path) -> ValidationError:
    try:
        load_config(path)
    except ConfigError as exc:
        if isinstance(exc.__cause__, ValidationError):
            return exc.__cause__
        msg = "missing validation error"
        raise AssertionError(msg) from exc
    msg = "expected validation error"
    raise AssertionError(msg)


def _has_loc(error: ValidationError, expected: tuple[object, ...]) -> bool:
    return any(err["loc"] == expected for err in error.errors())


def test_load_valid_config_minimum_required_fields() -> None:
    config = load_config(fixture_path("config/minimal_valid.toml"))

    assert config.slack.webhook_url == "https://hooks.slack.com/services/T000/B000/XXX"
    assert config.blogs[0].name == "Example Blog"
    assert config.blogs[0].url == "https://example.com"


@pytest.mark.parametrize(
    ("content", "expected_loc"),
    [
        pytest.param(
            fixture_path("config/missing_slack.toml"),
            ("slack",),
            id="missing_slack_webhook_url",
        ),
        pytest.param(
            fixture_path("config/missing_blog_url.toml"),
            ("blogs", 0, "url"),
            id="missing_blog_url",
        ),
        pytest.param(
            fixture_path("config/missing_blog_name.toml"),
            ("blogs", 0, "name"),
            id="missing_blog_name",
        ),
    ],
)
def test_missing_required_field_raises_error(content: Path, expected_loc: tuple[object, ...]) -> None:
    error = _load_validation_error(content)

    assert _has_loc(error, expected_loc)


@pytest.mark.parametrize(
    ("content", "expected_loc"),
    [
        pytest.param(
            fixture_path("config/invalid_slack_url.toml"),
            ("slack", "webhook_url"),
            id="invalid_slack_url",
        ),
        pytest.param(
            fixture_path("config/invalid_blog_url.toml"),
            ("blogs", 0, "url"),
            id="invalid_blog_url",
        ),
    ],
)
def test_invalid_url_raises_validation_error(content: Path, expected_loc: tuple[object, ...]) -> None:
    error = _load_validation_error(content)

    assert _has_loc(error, expected_loc)


def test_load_empty_blogs_raises_validation_error() -> None:
    error = _load_validation_error(fixture_path("config/empty_blogs.toml"))

    assert _has_loc(error, ("blogs",))


@pytest.mark.parametrize(
    ("content", "expected_loc"),
    [
        pytest.param(
            fixture_path("config/empty_slack_url.toml"),
            ("slack", "webhook_url"),
            id="empty_slack_url",
        ),
        pytest.param(
            fixture_path("config/empty_blog_name.toml"),
            ("blogs", 0, "name"),
            id="empty_blog_name",
        ),
        pytest.param(
            fixture_path("config/empty_blog_url.toml"),
            ("blogs", 0, "url"),
            id="empty_blog_url",
        ),
    ],
)
def test_empty_string_fields_raise_validation_error(content: Path, expected_loc: tuple[object, ...]) -> None:
    error = _load_validation_error(content)

    assert _has_loc(error, expected_loc)


def test_invalid_toml_raises_error() -> None:
    with pytest.raises(ConfigError, match="toml parse error"):
        load_config(fixture_path("config/invalid_toml.toml"))


@pytest.mark.parametrize(
    ("content", "expected_error"),
    [
        pytest.param(
            fixture_path("config/type_mismatch_slack_url.toml"),
            ValidationError,
            id="type_mismatch_slack_url",
        ),
        pytest.param(
            fixture_path("config/type_mismatch_blog_url.toml"),
            ValidationError,
            id="type_mismatch_blog_url",
        ),
        pytest.param(
            fixture_path("config/type_mismatch_blogs_list.toml"),
            ValidationError,
            id="type_mismatch_blogs_list",
        ),
    ],
)
def test_type_mismatch_raises_validation_error(content: Path, expected_error: type[Exception]) -> None:
    error = _load_validation_error(content)

    assert isinstance(error, expected_error)


@pytest.mark.parametrize(
    ("content", "expected_loc"),
    [
        pytest.param(
            fixture_path("config/extra_field_slack.toml"),
            ("slack", "extra"),
            id="extra_field_slack",
        ),
        pytest.param(
            fixture_path("config/extra_field_blog.toml"),
            ("blogs", 0, "extra"),
            id="extra_field_blog",
        ),
        pytest.param(
            fixture_path("config/extra_field_root.toml"),
            ("extra",),
            id="extra_field_root",
        ),
    ],
)
def test_extra_fields_raise_validation_error(content: Path, expected_loc: tuple[object, ...]) -> None:
    error = _load_validation_error(content)

    assert _has_loc(error, expected_loc)


def test_env_var_overrides_slack_webhook_url(monkeypatch: pytest.MonkeyPatch) -> None:
    override_url = "https://hooks.slack.com/services/T000/B000/OVERRIDE"
    monkeypatch.setenv("SLACK_WEBHOOK_URL", override_url)

    config = load_config(fixture_path("config/minimal_valid.toml"))

    assert config.slack.webhook_url == override_url
