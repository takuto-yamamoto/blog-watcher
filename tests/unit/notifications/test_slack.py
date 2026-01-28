import json
from collections.abc import AsyncIterator

import httpx
import pytest
import respx

from blog_watcher.config.models import SlackConfig
from blog_watcher.notifications.models import Notification
from blog_watcher.notifications.slack import SlackNotifier

WEBHOOK_URL = "https://hooks.slack.com/services/T00/B00/xxx"


@pytest.fixture
async def notifier() -> AsyncIterator[SlackNotifier]:
    async with httpx.AsyncClient() as client:
        yield SlackNotifier(client, SlackConfig(webhook_url=WEBHOOK_URL))


@pytest.mark.unit
class TestSlackNotifier:
    @respx.mock
    async def test_send_posts_expected_payload(self, notifier: SlackNotifier) -> None:
        route = respx.post(WEBHOOK_URL).mock(return_value=httpx.Response(200, text="ok"))
        notification = Notification(title="New Post", body="A new article.", url="https://example.com/post")

        await notifier.send(notification)

        payload = json.loads(route.calls[0].request.content)
        assert route.call_count == 1
        assert "<https://example.com/post>" in payload["text"]
