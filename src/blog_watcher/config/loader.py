from __future__ import annotations

import os
import tomllib
from typing import TYPE_CHECKING

from pydantic import ValidationError

from .errors import ConfigError
from .models import AppConfig

if TYPE_CHECKING:
    from pathlib import Path


def _format_error_location(loc: tuple[object, ...]) -> str:
    if not loc:
        return "config"
    parts: list[str] = []
    for item in loc:
        if isinstance(item, int):
            if parts:
                parts[-1] = f"{parts[-1]}[{item}]"
            else:
                parts.append(f"[{item}]")
        else:
            parts.append(str(item))
    return ".".join(parts)


def load_config(path: Path) -> AppConfig:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        msg = "toml parse error"
        raise ConfigError(msg) from exc

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
        details = ", ".join(
            f"{_format_error_location(error['loc'])}: {error['msg']}"
            for error in exc.errors()
        )
        msg = f"config validation error: {details}" if details else "config validation error"
        raise ConfigError(msg) from exc
