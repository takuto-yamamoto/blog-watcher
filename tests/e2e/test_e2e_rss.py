import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

from tests.e2e.helpers import (
    list_blog_states,
    load_blog_config,
    load_env,
)
from tests.e2e.helpers.slack import list_messages

E2E_ROOT = Path(__file__).resolve().parent
CONFIG_PATH = E2E_ROOT / "config.toml"
DB_PATH = E2E_ROOT / "blog_states.sqlite"


def main() -> None:
    env = load_env()
    blog_configs = load_blog_config(CONFIG_PATH)

    DB_PATH.unlink(missing_ok=True)

    subprocess.run(
        [sys.executable, "-m", "blog_watcher.main", "run", "-c", str(CONFIG_PATH), "--once"],
        check=True,
    )

    blog_states = list_blog_states(DB_PATH)
    blog_state_hostnames = {urlparse(state.blog_id).hostname for state in blog_states}

    assert len(blog_states) == len(blog_configs), "blog states count mismatch"
    for blog_config in blog_configs:
        blog_hostname = urlparse(blog_config.url).hostname
        assert blog_hostname in blog_state_hostnames, f"missing blog state for {blog_hostname}"

    for blog_state in blog_states:
        assert blog_state.last_checked_at is not None, f"last_checked_at missing for {blog_state.blog_id}"
        assert blog_state.url_fingerprint is not None, f"url_fingerprint missing for {blog_state.blog_id}"
        assert blog_state.feed_url is not None, f"feed_url missing for {blog_state.blog_id}"
        assert blog_state.recent_entry_keys is not None, f"recent_entry_keys missing for {blog_state.blog_id}"
        assert blog_state.last_changed_at is not None, f"last_changed_at missing for {blog_state.blog_id}"
        assert blog_state.consecutive_errors == 0, f"consecutive_errors not zero for {blog_state.blog_id}"

    messages = list_messages(env)
    assert messages, "No slack messages found"

    blog_names = {bc.name for bc in blog_configs}
    for name in blog_names:
        assert any(name in msg for msg in messages), f"Slack message missing for {name}"
