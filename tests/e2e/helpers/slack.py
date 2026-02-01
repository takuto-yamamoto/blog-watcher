import httpx

from tests.e2e.helpers.env import SlackConfig

SLACK_CONVERSATIONS_HISTORY_URL = "https://slack.com/api/conversations.history"


def list_messages(config: SlackConfig, *, limit: int = 5) -> list[str]:
    response = httpx.get(
        SLACK_CONVERSATIONS_HISTORY_URL,
        headers={"Authorization": f"Bearer {config.bot_token}"},
        params={"channel": config.channel_id, "limit": limit},
    )
    response.raise_for_status()

    data = response.json()
    if not data.get("ok"):
        msg = f"Slack API error: {data.get('error', 'unknown')}"
        raise RuntimeError(msg)

    return [m["text"] for m in data["messages"] if m.get("bot_id")]
