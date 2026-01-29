from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

import structlog

if TYPE_CHECKING:
    from collections.abc import MutableMapping

_SECRET_KEY_PATTERN = re.compile(r"(token|api_key|apikey|authorization|cookie|webhook|secret|password)", re.IGNORECASE)
_URL_SECRET_PATTERN = re.compile(r"(token|api_key|apikey|access_token)=([^&]+)")
_CONTROL_CHARS_PATTERN = re.compile(r"[\x00-\x1f\x7f]")
_MAX_VALUE_LENGTH = 4000


def _escape_control_char(match: re.Match[str]) -> str:
    char = match.group(0)
    if char == "\n":
        return "\\n"
    if char == "\r":
        return "\\r"
    if char == "\t":
        return "\\t"
    return f"\\x{ord(char):02x}"


def _sanitize_value(value: object) -> object:
    if isinstance(value, str):
        sanitized = _CONTROL_CHARS_PATTERN.sub(_escape_control_char, value)
        if _URL_SECRET_PATTERN.search(sanitized):
            sanitized = _URL_SECRET_PATTERN.sub(r"\1=***", sanitized)
        if "hooks.slack.com/services/" in sanitized:
            sanitized = re.sub(r"hooks\.slack\.com/services/[^\s>]+", "hooks.slack.com/services/***", sanitized)
        if len(sanitized) > _MAX_VALUE_LENGTH:
            return sanitized[:_MAX_VALUE_LENGTH] + "..."
        return sanitized
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {key: _sanitize_value(val) for key, val in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_sanitize_value(val) for val in value]
    return str(value)


def _sanitize_event(_: object, __: object, event_dict: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in event_dict.items():
        if _SECRET_KEY_PATTERN.search(key):
            sanitized[key] = "***"
        else:
            sanitized[key] = _sanitize_value(value)
    return sanitized


def _add_timestamp(_: object, __: object, event_dict: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    event_dict["timestamp"] = datetime.now(UTC).isoformat()
    return event_dict


def _render_json(_: object, __: object, event_dict: MutableMapping[str, Any]) -> str:
    return json.dumps(event_dict, ensure_ascii=False)


def _parse_level() -> str:
    level = os.environ.get("LOG_LEVEL", "INFO").upper()
    if level not in {"DEBUG", "INFO", "WARNING", "ERROR"}:
        return "INFO"
    return level


def configure_logging() -> structlog.BoundLogger:
    format_hint = os.environ.get("LOG_FORMAT", "json").lower()
    level = _parse_level()

    processors: list[structlog.types.Processor] = [
        _sanitize_event,
        _add_timestamp,
        structlog.processors.add_log_level,
    ]
    if format_hint == "console":
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors.append(_render_json)

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )

    return cast("structlog.BoundLogger", structlog.get_logger())


def get_logger(name: str) -> structlog.BoundLogger:
    return cast("structlog.BoundLogger", structlog.get_logger(name))
