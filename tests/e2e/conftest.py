from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from tests.e2e.helpers import load_env, start_fake_server, write_temp_config
from tests.e2e.helpers.server import Scenario

if TYPE_CHECKING:
    from collections.abc import Generator

    from tests.e2e.helpers.env import E2eEnv

E2E_ROOT = Path(__file__).resolve().parent
DB_PATH = E2E_ROOT / "blog_states.sqlite"


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
def tmp_rss_config(fake_rss_server: int) -> Generator[Path, None, None]:
    path = write_temp_config(fake_rss_server, Scenario.RSS)
    yield path
    path.unlink(missing_ok=True)


@pytest.fixture
def tmp_sitemap_config(fake_sitemap_server: int) -> Generator[Path, None, None]:
    path = write_temp_config(fake_sitemap_server, Scenario.SITEMAP)
    yield path
    path.unlink(missing_ok=True)


@pytest.fixture
def db_path() -> Generator[Path, None, None]:
    DB_PATH.unlink(missing_ok=True)
    yield DB_PATH
    DB_PATH.unlink(missing_ok=True)
