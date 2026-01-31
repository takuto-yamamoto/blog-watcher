import httpx

from tests.e2e.helpers.env import E2eEnv

SLACK_CONVERSATIONS_HISTORY_URL = "https://slack.com/api/conversations.history"


def list_messages(env: E2eEnv, *, limit: int = 5) -> list[str]:
    response = httpx.get(
        SLACK_CONVERSATIONS_HISTORY_URL,
        headers={"Authorization": f"Bearer {env.slack.bot_token}"},
        params={"channel": env.slack.channel_id, "limit": limit},
    )
    response.raise_for_status()

    data = response.json()
    if not data.get("ok"):
        msg = f"Slack API error: {data.get('error', 'unknown')}"
        raise RuntimeError(msg)

    return [m["text"] for m in data["messages"] if m.get("bot_id")]
