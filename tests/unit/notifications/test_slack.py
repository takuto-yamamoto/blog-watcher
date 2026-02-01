import json
from collections.abc import AsyncIterator

import httpx
import pytest
import respx

from blog_watcher.config import SlackConfig
from blog_watcher.notification import Notification, SlackNotifier

WEBHOOK_URL = "https://hooks.slack.com/services/T00/B00/xxx"


@pytest.fixture
async def notifier() -> AsyncIterator[SlackNotifier]:
    async with httpx.AsyncClient() as client:
        yield SlackNotifier(client, SlackConfig(webhook_url=WEBHOOK_URL))


@pytest.mark.unit
class TestSlackNotifier:
    @pytest.mark.parametrize(
        ("url", "expected_fallback", "expected_blocks"),
        [
            (
                "https://example.com/post",
                "New Post - <https://example.com/post>",
                [
                    {"type": "header", "text": {"type": "plain_text", "text": "New Post"}},
                    {"type": "section", "text": {"type": "mrkdwn", "text": "<https://example.com/post|A new article.>"}},
                ],
            ),
            (
                None,
                "New Post",
                [
                    {"type": "header", "text": {"type": "plain_text", "text": "New Post"}},
                    {"type": "section", "text": {"type": "mrkdwn", "text": "A new article."}},
                ],
            ),
        ],
    )
    @respx.mock
    async def test_send_posts_expected_payload(
        self,
        notifier: SlackNotifier,
        url: str | None,
        expected_fallback: str,
        expected_blocks: list[dict[str, object]],
    ) -> None:
        route = respx.post(WEBHOOK_URL).mock(return_value=httpx.Response(200, text="ok"))
        notification = Notification(title="New Post", body="A new article.", url=url)

        await notifier.send(notification)

        payload = json.loads(route.calls[0].request.content)
        assert route.call_count == 1
        assert payload["text"] == expected_fallback
        assert payload["blocks"] == expected_blocks

    @respx.mock
    async def test_send_retries_on_server_error(self, notifier: SlackNotifier) -> None:
        route = respx.post(WEBHOOK_URL).mock(
            side_effect=[
                httpx.Response(500, text="Internal Server Error"),
                httpx.Response(503, text="Service Unavailable"),
                httpx.Response(200, text="ok"),
            ]
        )
        notification = Notification(title="New Post", body="A new article.", url="https://example.com/post")

        await notifier.send(notification)

        assert route.call_count == 3

    @respx.mock
    async def test_send_fails_after_max_retries(self, notifier: SlackNotifier) -> None:
        route = respx.post(WEBHOOK_URL).mock(return_value=httpx.Response(500, text="Internal Server Error"))
        notification = Notification(title="New Post", body="A new article.", url="https://example.com/post")

        with pytest.raises(httpx.HTTPStatusError):
            await notifier.send(notification)

        assert route.call_count == 3

    @respx.mock
    async def test_send_retries_on_timeout(self, notifier: SlackNotifier) -> None:
        route = respx.post(WEBHOOK_URL).mock(
            side_effect=[
                httpx.TimeoutException("timeout"),
                httpx.Response(200, text="ok"),
            ]
        )
        notification = Notification(title="New Post", body="A new article.", url="https://example.com/post")

        await notifier.send(notification)

        assert route.call_count == 2
