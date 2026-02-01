from __future__ import annotations

import subprocess
import sys
from typing import TYPE_CHECKING

from tests.e2e.assertions import (
    assert_all_blogs_tracked,
    assert_blog_states_populated,
    assert_no_change_on_rerun,
    assert_slack_notifications_sent,
)
from tests.e2e.helpers import list_blog_states, load_blog_config

if TYPE_CHECKING:
    from pathlib import Path

    from tests.e2e.helpers.env import E2eEnv


def test_rss_e2e(env: E2eEnv, tmp_rss_config: Path, db_path: Path) -> None:
    blogs = load_blog_config(tmp_rss_config)
    cmd = [sys.executable, "-m", "blog_watcher.main", "-c", str(tmp_rss_config), "--once", "--db-path", str(db_path)]

    # Run 1: initial discovery
    subprocess.run(cmd, check=True)

    blog_states_run1 = list_blog_states(db_path)

    assert_all_blogs_tracked(blog_states_run1, blogs)
    assert_blog_states_populated(blog_states_run1)
    assert_slack_notifications_sent(env.slack, blogs)

    # Run 2: cached URLs should be reused, no false changes
    subprocess.run(cmd, check=True)

    blog_states_run2 = list_blog_states(db_path)

    assert_all_blogs_tracked(blog_states_run2, blogs)
    assert_no_change_on_rerun(blog_states_run1, blog_states_run2)
