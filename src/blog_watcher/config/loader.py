from __future__ import annotations

import os
import tomllib
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from .errors import ConfigError
from .models import AppConfig, BlogConfig, SlackConfig

if TYPE_CHECKING:
    from pathlib import Path


def _is_valid_url(value: str) -> bool:
    parsed = urlparse(value)
    return bool(parsed.scheme) and bool(parsed.netloc)


def _require_str(mapping: dict[str, Any], key: str, context: str) -> str:
    value = mapping.get(key)
    if value is None or value == "":
        msg = f"{context}.{key} is required"
        raise ConfigError(msg)
    if not isinstance(value, str):
        msg = f"{context}.{key} must be a string"
        raise ConfigError(msg)
    return value


def _parse_slack(data: dict[str, Any]) -> SlackConfig:
    slack = data.get("slack")
    if slack is None:
        msg = "slack.webhook_url is required"
        raise ConfigError(msg)
    if not isinstance(slack, dict):
        msg = "slack must be a table"
        raise ConfigError(msg)
    slack_url = os.environ.get("SLACK_WEBHOOK_URL") or _require_str(slack, "webhook_url", "slack")
    if not _is_valid_url(slack_url):
        msg = "slack.webhook_url must be a valid URL"
        raise ConfigError(msg)
    return SlackConfig(webhook_url=slack_url)


def _parse_blogs(data: dict[str, Any]) -> list[BlogConfig]:
    blogs_raw = data.get("blogs")
    if blogs_raw is None:
        msg = "blogs must be a list"
        raise ConfigError(msg)
    if not isinstance(blogs_raw, list):
        msg = "blogs must be a list"
        raise ConfigError(msg)
    if not blogs_raw:
        msg = "blogs must be non-empty"
        raise ConfigError(msg)

    blogs: list[BlogConfig] = []
    for index, blog in enumerate(blogs_raw):
        if not isinstance(blog, dict):
            msg = f"blogs[{index}] must be a table"
            raise ConfigError(msg)
        url = _require_str(blog, "url", f"blogs[{index}]")
        if not _is_valid_url(url):
            msg = f"blogs[{index}].url must be a valid URL"
            raise ConfigError(msg)
        blogs.append(BlogConfig(url=url))
    return blogs


def load_config(path: Path) -> AppConfig:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        msg = "toml parse error"
        raise ConfigError(msg) from exc
    if not isinstance(data, dict):
        msg = "config must be a table"
        raise ConfigError(msg)

    slack = _parse_slack(data)
    blogs = _parse_blogs(data)

    return AppConfig(slack=slack, blogs=blogs)
