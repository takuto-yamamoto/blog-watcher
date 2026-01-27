"""Shared pytest configuration for all test levels."""

from __future__ import annotations

import os

from hypothesis import HealthCheck, settings

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
