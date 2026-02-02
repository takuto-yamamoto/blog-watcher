from __future__ import annotations

import subprocess
import sys
import uuid
from typing import TYPE_CHECKING

from tests.e2e.assertions import (
    assert_all_blogs_tracked,
    assert_blog_states_populated_full,
    assert_change_detected,
    assert_slack_notifications_sent,
)
from tests.e2e.helpers import Mode, list_blog_states, load_blog_config, set_server_mode, write_temp_config

if TYPE_CHECKING:
    from pathlib import Path

    from tests.e2e.helpers.env import E2eEnv


def _new_run_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


def _run_once(config_path: Path, db_path: Path) -> None:
    subprocess.run(
        [sys.executable, "-m", "blog_watcher.main", "-c", str(config_path), "--once", "--db-path", str(db_path)],
        check=True,
    )


def test_full_fallback_e2e(env: E2eEnv, fake_full_server: int, db_path: Path) -> None:
    port = fake_full_server
    set_server_mode(port, Mode.BASELINE)

    run1_id = _new_run_id("full-run1")
    run2_id = _new_run_id("full-run2")

    run1_config = write_temp_config(port, run1_id)
    blogs = load_blog_config(run1_config)

    # Run 1: baseline — both feed and sitemap discovered, change detected (first run)
    _run_once(run1_config, db_path)

    blog_states_run1 = list_blog_states(db_path)

    assert_all_blogs_tracked(blog_states_run1, blogs)
    assert_blog_states_populated_full(blog_states_run1)
    assert_slack_notifications_sent(env.slack, includes={run1_id}, excludes=set())

    # Run 2: RSS feed unchanged, sitemap has new URL → fallback detection
    set_server_mode(port, Mode.SITEMAP_CHANGED)
    run2_config = write_temp_config(port, run2_id)
    _run_once(run2_config, db_path)

    blog_states_run2 = list_blog_states(db_path)

    assert_all_blogs_tracked(blog_states_run2, blogs)
    assert_change_detected(blog_states_run1, blog_states_run2)
    assert_slack_notifications_sent(env.slack, includes={run1_id, run2_id}, excludes=set())
