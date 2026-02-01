from __future__ import annotations

import subprocess
import sys
import uuid
from typing import TYPE_CHECKING

from tests.e2e.assertions import (
    assert_all_blogs_tracked,
    assert_blog_states_populated_sitemap,
    assert_change_detected,
    assert_no_change_on_rerun,
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


def test_sitemap_e2e(env: E2eEnv, fake_sitemap_server: int, db_path: Path) -> None:
    port = fake_sitemap_server
    set_server_mode(port, Mode.BASELINE)

    run1_id = _new_run_id("sitemap-run1")
    run2_id = _new_run_id("sitemap-run2")
    run3_id = _new_run_id("sitemap-run3")

    run1_config = write_temp_config(port, run1_id)
    blogs = load_blog_config(run1_config)

    # Run 1: initial discovery
    _run_once(run1_config, db_path)

    blog_states_run1 = list_blog_states(db_path)

    assert_all_blogs_tracked(blog_states_run1, blogs)
    assert_blog_states_populated_sitemap(blog_states_run1)
    assert_slack_notifications_sent(env.slack, includes={run1_id}, excludes=set())

    # Run 2: cached URLs should be reused, no false changes
    run2_config = write_temp_config(port, run2_id)
    _run_once(run2_config, db_path)

    blog_states_run2 = list_blog_states(db_path)

    assert_all_blogs_tracked(blog_states_run2, blogs)
    assert_no_change_on_rerun(blog_states_run1, blog_states_run2)
    assert_slack_notifications_sent(env.slack, includes={run1_id}, excludes={run2_id})

    # Run 3: new article should be detected
    set_server_mode(port, Mode.NEW_ARTICLE)
    run3_config = write_temp_config(port, run3_id)
    _run_once(run3_config, db_path)

    blog_states_run3 = list_blog_states(db_path)

    assert_all_blogs_tracked(blog_states_run3, blogs)
    assert_change_detected(blog_states_run2, blog_states_run3)
    assert_slack_notifications_sent(env.slack, includes={run1_id, run3_id}, excludes={run2_id})
