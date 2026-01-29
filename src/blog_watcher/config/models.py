from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SlackConfig:
    webhook_url: str


@dataclass(frozen=True, slots=True)
class BlogConfig:
    name: str
    url: str


@dataclass(frozen=True, slots=True)
class AppConfig:
    slack: SlackConfig
    blogs: list[BlogConfig]
