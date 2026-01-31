from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, field_validator

from blog_watcher.detection.url_normalizer import normalize_url

if TYPE_CHECKING:
    from collections.abc import Mapping


def _is_valid_url(value: str) -> bool:
    parsed = urlparse(value)
    return bool(parsed.scheme) and bool(parsed.netloc)


class SlackConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    webhook_url: str

    @field_validator("webhook_url")
    @classmethod
    def _validate_webhook_url(cls, value: str) -> str:
        if not _is_valid_url(value):
            msg = "must be a valid URL"
            raise ValueError(msg)
        return value


class BlogConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    url: str

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        if value == "":
            msg = "is required"
            raise ValueError(msg)
        return value

    @field_validator("url")
    @classmethod
    def _validate_url(cls, value: str) -> str:
        if not _is_valid_url(value):
            msg = "must be a valid URL"
            raise ValueError(msg)
        return value

    @property
    def blog_id(self) -> str:
        return normalize_url(self.url)


class AppConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    slack: SlackConfig
    blogs: list[BlogConfig]

    @field_validator("blogs")
    @classmethod
    def _validate_blogs(cls, value: list[BlogConfig]) -> list[BlogConfig]:
        if not value:
            msg = "must be non-empty"
            raise ValueError(msg)
        return value

    @classmethod
    def from_raw(cls, data: Mapping[str, object]) -> AppConfig:
        return cls.model_validate(data)
