from __future__ import annotations

from pathlib import Path

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "test_utils" / "fixture"


def fixture_path(path: str) -> Path:
    return FIXTURE_DIR / path


def read_fixture(path: str) -> str:
    return fixture_path(path).read_text(encoding="utf-8")


def read_fixture_bytes(path: str) -> bytes:
    return fixture_path(path).read_bytes()
