from __future__ import annotations

import os
import tomllib
from typing import TYPE_CHECKING

from pydantic import ValidationError

from .errors import ConfigError
from .models import AppConfig

if TYPE_CHECKING:
    from pathlib import Path


def load_config(path: Path) -> AppConfig:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        msg = "toml parse error"
        raise ConfigError(msg) from exc
    if not isinstance(data, dict):
        msg = "config must be a table"
        raise ConfigError(msg)

    override_url = os.environ.get("SLACK_WEBHOOK_URL")
    if override_url:
        data = dict(data)
        slack = data.get("slack")
        slack_dict: dict[str, object] = dict(slack) if isinstance(slack, dict) else {}
        slack_dict["webhook_url"] = override_url
        data["slack"] = slack_dict

    try:
        return AppConfig.from_raw(data)
    except ValidationError as exc:
        msg = "config validation error"
        raise ConfigError(msg) from exc
