import re
from pathlib import Path

import pytest

from blog_watcher.config import load_config


def _config_path(name: str) -> Path:
    return Path(__file__).resolve().parents[2] / "fixtures" / "config" / name


def test_load_valid_config_minimum_required_fields() -> None:
    config_path = _config_path("minimal_valid.toml")
    config = load_config(config_path)
    assert config.slack.webhook_url == "https://hooks.slack.com/services/T000/B000/XXX"
    assert config.blogs[0].url == "https://example.com"


@pytest.mark.parametrize(
    ("content", "missing_field"),
    [
        pytest.param(
            _config_path("missing_slack.toml"),
            "slack.webhook_url",
            id="missing_slack_webhook_url",
        ),
        pytest.param(
            _config_path("missing_blog_url.toml"),
            "blogs[0].url",
            id="missing_blog_url",
        ),
    ],
)
def test_missing_required_field_raises_error(content: Path, missing_field: str) -> None:
    with pytest.raises(ValueError, match=re.escape(missing_field)):
        load_config(content)


@pytest.mark.parametrize(
    ("content", "invalid_field"),
    [
        pytest.param(
            _config_path("invalid_slack_url.toml"),
            "slack.webhook_url",
            id="invalid_slack_url",
        ),
        pytest.param(
            _config_path("invalid_blog_url.toml"),
            "blogs[0].url",
            id="invalid_blog_url",
        ),
    ],
)
def test_invalid_url_raises_validation_error(content: Path, invalid_field: str) -> None:
    with pytest.raises(ValueError, match=re.escape(invalid_field)):
        load_config(content)


def test_load_empty_blogs_raises_validation_error() -> None:
    config_path = _config_path("empty_blogs.toml")
    with pytest.raises(ValueError, match="invalid"):
        load_config(config_path)


def test_invalid_toml_raises_error() -> None:
    config_path = _config_path("invalid_toml.toml")
    with pytest.raises(ValueError, match="parse"):
        load_config(config_path)


@pytest.mark.parametrize(
    "content",
    [
        _config_path("type_mismatch_slack_url.toml"),
        _config_path("type_mismatch_blog_url.toml"),
        _config_path("type_mismatch_blogs_list.toml"),
    ],
)
def test_type_mismatch_raises_validation_error(content: Path) -> None:
    with pytest.raises(TypeError, match=r"string|list"):
        load_config(content)


def test_env_var_overrides_slack_webhook_url(monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = _config_path("minimal_valid.toml")
    override_url = "https://hooks.slack.com/services/T000/B000/OVERRIDE"

    monkeypatch.setenv("SLACK_WEBHOOK_URL", override_url)

    config = load_config(config_path)

    assert config.slack.webhook_url == override_url
