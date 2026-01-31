import pytest

from blog_watcher.observability.logging import (
    sanitize_event,
    sanitize_value,
)


def test_sanitize_masks_secrets_and_controls() -> None:
    value: dict[str, object] = {
        "payload": "line1\nline2\tvalue\rend",
        "url": "https://example.com?token=abc123",
        "webhook_url": "https://hooks.slack.com/services/T000/B000/XXX",
    }

    sanitized = sanitize_value(value)

    assert isinstance(sanitized, dict)
    assert sanitized["payload"] == "line1\\nline2\\tvalue\\rend"
    assert sanitized["url"] == "https://example.com?token=***"
    assert sanitized["webhook_url"] == "https://hooks.slack.com/services/***"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ({"key": "value", "nested": {"token": "secret"}}, {"key": "value", "nested": {"token": "secret"}}),
        (("item1", "item2"), ["item1", "item2"]),
        ({"item1", "item2"}, {"item1", "item2"}),
    ],
)
def test_sanitize_value_collections_and_primitives(value: object, expected: object) -> None:
    result = sanitize_value(value)
    if isinstance(value, set):
        assert isinstance(result, list)
        assert set(result) == expected
    else:
        assert result == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [(42, 42), (3.14, 3.14), (True, True), (None, None)],
)
def test_sanitize_value_primitives_passthrough(value: object, expected: object) -> None:
    assert sanitize_value(value) == expected


def test_sanitize_value_slack_url() -> None:
    value = "Webhook: https://hooks.slack.com/services/T000/B000/XXX"
    result = sanitize_value(value)
    assert result == "Webhook: https://hooks.slack.com/services/***"


def test_sanitize_value_url_with_token() -> None:
    value = "https://api.example.com?api_key=secret123&other=param"
    result = sanitize_value(value)
    assert result == "https://api.example.com?api_key=***&other=param"


def test_sanitize_value_truncation() -> None:
    long_value = "a" * 5000
    result = sanitize_value(long_value)
    assert isinstance(result, str)
    assert len(result) == 4003  # 4000 + "..."
    assert result.endswith("...")


def test_sanitize_value_control_char_fallback_hex() -> None:
    value = "start\x07end"
    result = sanitize_value(value)
    assert result == "start\\x07end"


def test_sanitize_value_unknown_type_to_str() -> None:
    class Thing:
        def __str__(self) -> str:
            return "thing"

    result = sanitize_value(Thing())
    assert result == "thing"


def test_sanitize_event_masks_secret_keys() -> None:
    event = {
        "api_key": "secret",
        "apikey": "secret",
        "authorization": "Bearer token",
        "cookie": "session=xyz",
        "webhook": "https://example.com",
        "secret": "mysecret",
        "password": "pass123",
        "normal_key": "visible",
    }
    result = sanitize_event(None, None, event)
    assert result["api_key"] == "***"
    assert result["apikey"] == "***"
    assert result["authorization"] == "***"
    assert result["cookie"] == "***"
    assert result["webhook"] == "***"
    assert result["secret"] == "***"  # noqa: S105
    assert result["password"] == "***"  # noqa: S105
    assert result["normal_key"] == "visible"
