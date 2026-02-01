from __future__ import annotations

import subprocess
import sys
from typing import TYPE_CHECKING

from tests.e2e.assertions import assert_all_blogs_tracked, assert_blog_states_populated, assert_slack_notifications_sent
from tests.e2e.helpers import list_blog_states, load_blog_config

if TYPE_CHECKING:
    from pathlib import Path

    from tests.e2e.helpers.env import E2eEnv


def test_rss_e2e(env: E2eEnv, tmp_config: Path, db_path: Path) -> None:
    blogs = load_blog_config(tmp_config)

    subprocess.run(
        [sys.executable, "-m", "blog_watcher.main", "-c", str(tmp_config), "--once", "--db-path", str(db_path)],
        check=True,
    )

    blog_states = list_blog_states(db_path)

    assert_all_blogs_tracked(blog_states, blogs)
    assert_blog_states_populated(blog_states)
    assert_slack_notifications_sent(env.slack, blogs)
