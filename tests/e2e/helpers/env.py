import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class SlackEnv:
    webhook_url: str
    channel_id: str
    bot_token: str


@dataclass(frozen=True)
class E2eEnv:
    slack: SlackEnv


def _require_env(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        msg = f"Missing required environment variable: {key}. Set it in your environment or in a .env file at the project root."
        raise RuntimeError(msg)
    return value


def load_env() -> E2eEnv:
    env_path = Path(__file__).resolve().parents[3] / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    return E2eEnv(
        slack=SlackEnv(
            webhook_url=_require_env("SLACK_WEBHOOK_URL"),
            channel_id=_require_env("SLACK_CHANNEL_ID"),
            bot_token=_require_env("SLACK_BOT_TOKEN"),
        ),
    )
