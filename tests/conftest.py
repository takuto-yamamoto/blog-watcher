"""Shared pytest configuration for all test levels."""

from __future__ import annotations

import os
from pathlib import Path

from hypothesis import HealthCheck, settings

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def fixture_path(path: str) -> Path:
    return FIXTURES_DIR / path


def read_fixture(path: str) -> str:
    return fixture_path(path).read_text(encoding="utf-8")


def read_fixture_byte(path: str) -> bytes:
    return fixture_path(path).read_bytes()


# Configure Hypothesis global settings
settings.register_profile(
    "dev",
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
settings.register_profile(
    "ci",
    max_examples=100,
    deadline=5000,
)

if os.getenv("CI"):
    settings.load_profile("ci")
else:
    settings.load_profile("dev")
