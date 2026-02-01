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


def assert_no_change_on_rerun(before: list[BlogStateRow], after: list[BlogStateRow]) -> None:
    before_by_id = {s.blog_id: s for s in before}
    after_by_id = {s.blog_id: s for s in after}

    assert before_by_id.keys() == after_by_id.keys(), "blog_id set changed between runs"

    for blog_id, prev in before_by_id.items():
        curr = after_by_id[blog_id]
        assert curr.last_changed_at == prev.last_changed_at, (
            f"last_changed_at changed for {blog_id}: {prev.last_changed_at} -> {curr.last_changed_at}"
        )
        assert curr.feed_url == prev.feed_url, f"feed_url changed for {blog_id}"
        assert curr.sitemap_url == prev.sitemap_url, f"sitemap_url changed for {blog_id}"
        assert curr.url_fingerprint == prev.url_fingerprint, f"url_fingerprint changed for {blog_id}"
        assert curr.consecutive_errors == 0, f"consecutive_errors not zero for {blog_id} after rerun"


def assert_change_detected(before: list[BlogStateRow], after: list[BlogStateRow]) -> None:
    before_by_id = {s.blog_id: s for s in before}
    after_by_id = {s.blog_id: s for s in after}

    assert before_by_id.keys() == after_by_id.keys(), "blog_id set changed between runs"

    for blog_id, prev in before_by_id.items():
        curr = after_by_id[blog_id]
        assert curr.last_changed_at != prev.last_changed_at, f"last_changed_at did not change for {blog_id}"
        assert curr.url_fingerprint != prev.url_fingerprint, f"url_fingerprint did not change for {blog_id}"
        assert curr.consecutive_errors == 0, f"consecutive_errors not zero for {blog_id} after change"


def assert_slack_notifications_sent(
    config: SlackConfig,
    *,
    includes: set[str],
    excludes: set[str],
) -> None:
    messages = list_messages(config, limit=10)
    assert messages, "No slack messages found"

    for token in includes:
        assert any(token in msg for msg in messages), f"Slack message missing {token}"

    for token in excludes:
        assert all(token not in msg for msg in messages), f"Slack message unexpectedly contains {token}"
