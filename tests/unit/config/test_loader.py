import re
from pathlib import Path

import pytest
from tests.conftest import fixture_path

from blog_watcher.config import ConfigError, load_config


def test_load_valid_config_minimum_required_fields() -> None:
    config = load_config(fixture_path("config/minimal_valid.toml"))

    assert config.slack.webhook_url == "https://hooks.slack.com/services/T000/B000/XXX"
    assert config.blogs[0].url == "https://example.com"


@pytest.mark.parametrize(
    ("content", "missing_field"),
    [
        pytest.param(
            fixture_path("config/missing_slack.toml"),
            "slack.webhook_url",
            id="missing_slack_webhook_url",
        ),
        pytest.param(
            fixture_path("config/missing_blog_url.toml"),
            "blogs[0].url",
            id="missing_blog_url",
        ),
    ],
)
def test_missing_required_field_raises_error(content: Path, missing_field: str) -> None:
    with pytest.raises(ConfigError, match=re.escape(missing_field)):
        load_config(content)


@pytest.mark.parametrize(
    ("content", "invalid_field"),
    [
        pytest.param(
            fixture_path("config/invalid_slack_url.toml"),
            "slack.webhook_url",
            id="invalid_slack_url",
        ),
        pytest.param(
            fixture_path("config/invalid_blog_url.toml"),
            "blogs[0].url",
            id="invalid_blog_url",
        ),
    ],
)
def test_invalid_url_raises_validation_error(content: Path, invalid_field: str) -> None:
    with pytest.raises(ConfigError, match=re.escape(invalid_field)):
        load_config(content)


def test_load_empty_blogs_raises_validation_error() -> None:
    with pytest.raises(ConfigError, match="non-empty"):
        load_config(fixture_path("config/empty_blogs.toml"))


def test_invalid_toml_raises_error() -> None:
    with pytest.raises(ConfigError, match="parse"):
        load_config(fixture_path("config/invalid_toml.toml"))


@pytest.mark.parametrize(
    ("content", "expected_error"),
    [
        pytest.param(
            fixture_path("config/type_mismatch_slack_url.toml"),
            ConfigError,
            id="type_mismatch_slack_url",
        ),
        pytest.param(
            fixture_path("config/type_mismatch_blog_url.toml"),
            ConfigError,
            id="type_mismatch_blog_url",
        ),
        pytest.param(
            fixture_path("config/type_mismatch_blogs_list.toml"),
            ConfigError,
            id="type_mismatch_blogs_list",
        ),
    ],
)
def test_type_mismatch_raises_validation_error(content: Path, expected_error: type[Exception]) -> None:
    with pytest.raises(expected_error, match=r"string|list"):
        load_config(content)


def test_env_var_overrides_slack_webhook_url(monkeypatch: pytest.MonkeyPatch) -> None:
    override_url = "https://hooks.slack.com/services/T000/B000/OVERRIDE"
    monkeypatch.setenv("SLACK_WEBHOOK_URL", override_url)

    config = load_config(fixture_path("config/minimal_valid.toml"))

    assert config.slack.webhook_url == override_url
