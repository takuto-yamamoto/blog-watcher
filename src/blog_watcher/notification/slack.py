from http import HTTPStatus

import httpx
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from blog_watcher.config.models import SlackConfig
from blog_watcher.notification.base import Notifier
from blog_watcher.notification.models import Notification
from blog_watcher.observability import get_logger

logger = get_logger(__name__)


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
                    logger.warning("slack_send_failed", status_code=response.status_code)
                    response.raise_for_status()

        logger.info("slack_send_succeeded")

    @staticmethod
    def _build_payload(notification: Notification) -> dict[str, object]:
        blocks: list[dict[str, object]] = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": notification.title},
            },
        ]
        if notification.url is not None:
            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"<{notification.url}|{notification.body}>"},
                },
            )
        else:
            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": notification.body},
                },
            )
        # fallback for non-block-capable clients
        fallback = notification.title
        if notification.url is not None:
            fallback += f" - <{notification.url}>"
        return {"text": fallback, "blocks": blocks}
