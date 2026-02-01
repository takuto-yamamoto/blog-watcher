from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from tests.e2e.helpers import load_env, start_fake_server
from tests.e2e.helpers.server import Scenario

if TYPE_CHECKING:
    from collections.abc import Generator

    from tests.e2e.helpers.env import E2eEnv


DB_PATH = Path(__file__).resolve().parent / "blog_states.sqlite"


@pytest.fixture(scope="session")
def env() -> E2eEnv:
    return load_env()


@pytest.fixture
def fake_rss_server() -> Generator[int, None, None]:
    proc, port = start_fake_server(Scenario.RSS)
    yield port
    proc.terminate()
    proc.wait()


@pytest.fixture
def fake_sitemap_server() -> Generator[int, None, None]:
    proc, port = start_fake_server(Scenario.SITEMAP)
    yield port
    proc.terminate()
    proc.wait()


@pytest.fixture
def db_path() -> Generator[Path, None, None]:
    DB_PATH.unlink(missing_ok=True)
    yield DB_PATH
    DB_PATH.unlink(missing_ok=True)
