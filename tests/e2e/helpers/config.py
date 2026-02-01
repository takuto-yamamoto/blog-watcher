import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BlogEntry:
    name: str
    url: str


def load_blog_config(config_path: Path) -> list[BlogEntry]:
    with config_path.open("rb") as f:
        raw = tomllib.load(f)

    return [BlogEntry(name=b["name"], url=b["url"]) for b in raw["blogs"]]


def write_temp_config(port: int) -> Path:
    config_text = f"""
[slack]
webhook_url = "${{SLACK_WEBHOOK_URL}}"

[[blogs]]
name = "Dummy Blog for E2E Test"
url = "http://127.0.0.1:{port}"
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as tmp:
        tmp.write(config_text)

    return Path(tmp.name)
