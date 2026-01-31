import json
import os
from collections.abc import Generator
from typing import Any, cast
from unittest.mock import patch

import pytest
import structlog

from blog_watcher.observability.logging import configure_logging


@pytest.fixture(autouse=True)
def reset_structlog_defaults() -> Generator[None, None, None]:
    structlog.reset_defaults()
    yield
    structlog.reset_defaults()


def read_last_json_output(capsys: pytest.CaptureFixture[str]) -> dict[str, Any]:
    output = capsys.readouterr().out
    lines = [line for line in output.splitlines() if line.strip()]
    assert lines, "expected at least one log line"
    return cast("dict[str, Any]", json.loads(lines[-1]))


def test_json_log_contains_timestamp_and_level(capsys: pytest.CaptureFixture[str]) -> None:
    with patch.dict(os.environ, {"LOG_FORMAT": "json", "LOG_LEVEL": "INFO"}, clear=True):
        logger = configure_logging()
        logger.info("ping")
        out = read_last_json_output(capsys)
        assert out["event"] == "ping"
        assert out["level"] == "info"
        assert out["timestamp"].endswith("+00:00")


def test_console_log_emits_output(capsys: pytest.CaptureFixture[str]) -> None:
    with patch.dict(os.environ, {"LOG_FORMAT": "console", "LOG_LEVEL": "INFO"}, clear=True):
        logger = configure_logging()
        logger.info("hello")
        captured = capsys.readouterr().out
        assert "hello" in captured


def test_invalid_log_level_falls_back_to_info(capsys: pytest.CaptureFixture[str]) -> None:
    with patch.dict(os.environ, {"LOG_FORMAT": "json", "LOG_LEVEL": "nope"}, clear=True):
        logger = configure_logging()
        logger.debug("hidden")
        logger.info("visible")
        out = read_last_json_output(capsys)
        assert out["event"] == "visible"
