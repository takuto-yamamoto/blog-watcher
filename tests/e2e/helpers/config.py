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
