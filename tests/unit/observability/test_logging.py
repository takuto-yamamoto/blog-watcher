from blog_watcher.observability.logging import _sanitize_event


def test_sanitize_masks_secrets_and_controls() -> None:
    event: dict[str, object] = {
        "token": "secret-token",
        "payload": "line1\nline2\tvalue\rend",
        "url": "https://example.com?token=abc123",
        "webhook_url": "https://hooks.slack.com/services/T000/B000/XXX",
    }

    sanitized = _sanitize_event(None, None, event)

    assert sanitized["token"] == "***"  # noqa: S105
    assert sanitized["payload"] == "line1\\nline2\\tvalue\\rend"
    assert sanitized["url"] == "https://example.com?token=***"
    assert sanitized["webhook_url"] == "***"
