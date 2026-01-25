from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .models import AppConfig, BlogConfig, SlackConfig


def _is_valid_url(value: str) -> bool:
    parsed = urlparse(value)
    return bool(parsed.scheme) and bool(parsed.netloc)


def _require_str(mapping: dict[str, Any], key: str, context: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{context}.{key} is required")
    return value


def load_config(path: Path) -> AppConfig:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("config must be a table")

    slack = data.get("slack")
    if not isinstance(slack, dict):
        raise ValueError("slack.webhook_url is required")
    slack_url = os.environ.get("SLACK_WEBHOOK_URL") or _require_str(
        slack, "webhook_url", "slack"
    )
    if not _is_valid_url(slack_url):
        raise ValueError("slack.webhook_url must be a valid URL")

    blogs_raw = data.get("blogs")
    if not isinstance(blogs_raw, list) or not blogs_raw:
        raise ValueError("blogs must be a non-empty list")

    blogs: list[BlogConfig] = []
    for index, blog in enumerate(blogs_raw):
        if not isinstance(blog, dict):
            raise ValueError(f"blogs[{index}] must be a table")
        url = _require_str(blog, "url", f"blogs[{index}]")
        if not _is_valid_url(url):
            raise ValueError(f"blogs[{index}].url must be a valid URL")
        blogs.append(BlogConfig(url=url))

    return AppConfig(slack=SlackConfig(webhook_url=slack_url), blogs=blogs)
