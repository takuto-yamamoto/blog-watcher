from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlparse

from tests.e2e.helpers.slack import list_messages

if TYPE_CHECKING:
    from tests.e2e.helpers.config import BlogEntry
    from tests.e2e.helpers.database import BlogStateRow
    from tests.e2e.helpers.env import SlackConfig


def assert_all_blogs_tracked(blog_states: list[BlogStateRow], blogs: list[BlogEntry]) -> None:
    assert len(blog_states) == len(blogs), "blog states count mismatch"

    blog_state_hostnames = {urlparse(state.blog_id).hostname for state in blog_states}
    for blog in blogs:
        blog_hostname = urlparse(blog.url).hostname
        assert blog_hostname in blog_state_hostnames, f"missing blog state for {blog_hostname}"


def assert_blog_states_populated(blog_states: list[BlogStateRow]) -> None:
    for state in blog_states:
        assert state.last_checked_at is not None, f"last_checked_at missing for {state.blog_id}"
        assert state.url_fingerprint is not None, f"url_fingerprint missing for {state.blog_id}"
        assert state.feed_url is not None, f"feed_url missing for {state.blog_id}"
        assert state.recent_entry_keys is not None, f"recent_entry_keys missing for {state.blog_id}"
        assert state.last_changed_at is not None, f"last_changed_at missing for {state.blog_id}"
        assert state.consecutive_errors == 0, f"consecutive_errors not zero for {state.blog_id}"


def assert_blog_states_populated_sitemap(blog_states: list[BlogStateRow]) -> None:
    for state in blog_states:
        assert state.last_checked_at is not None, f"last_checked_at missing for {state.blog_id}"
        assert state.url_fingerprint is not None, f"url_fingerprint missing for {state.blog_id}"
        assert state.last_changed_at is not None, f"last_changed_at missing for {state.blog_id}"
        assert state.consecutive_errors == 0, f"consecutive_errors not zero for {state.blog_id}"


def assert_slack_notifications_sent(config: SlackConfig, blogs: list[BlogEntry]) -> None:
    messages = list_messages(config)
    assert messages, "No slack messages found"

    blog_names = {blog.name for blog in blogs}
    for name in blog_names:
        assert any(name in msg for msg in messages), f"Slack message missing for {name}"
