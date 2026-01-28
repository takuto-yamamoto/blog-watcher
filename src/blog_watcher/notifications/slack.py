from http import HTTPStatus

import httpx
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from blog_watcher.config.models import SlackConfig
from blog_watcher.notifications.base import Notifier
from blog_watcher.notifications.models import Notification


class SlackNotifier(Notifier):
    def __init__(self, client: httpx.AsyncClient, config: SlackConfig) -> None:
        self._client = client
        self._config = config

    async def send(self, notification: Notification) -> None:
        payload = self._build_payload(notification)

        async for attempt in AsyncRetrying(
            retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
            wait=wait_exponential(multiplier=1, max=60),
            stop=stop_after_attempt(3),
            reraise=True,
        ):
            with attempt:
                response = await self._client.post(self._config.webhook_url, json=payload)
                if response.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
                    response.raise_for_status()

    @staticmethod
    def _build_payload(notification: Notification) -> dict[str, object]:
        text = f"*{notification.title}*\n{notification.body}"
        if notification.url is not None:
            text += f"\n<{notification.url}>"
        return {"text": text}
