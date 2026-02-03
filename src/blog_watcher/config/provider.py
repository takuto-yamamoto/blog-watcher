from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from blog_watcher.config.errors import ConfigError
from blog_watcher.config.loader import load_config

if TYPE_CHECKING:
    from pathlib import Path

    from blog_watcher.config.models import AppConfig


class ConfigProvider(Protocol):
    def get(self) -> AppConfig: ...


@dataclass(slots=True)
class StaticConfigProvider:
    config: AppConfig

    def get(self) -> AppConfig:
        return self.config


class FileConfigProvider:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._last_mtime: float | None = None
        self._current: AppConfig | None = None

    def get(self) -> AppConfig:
        try:
            mtime = self._path.stat().st_mtime
        except FileNotFoundError as exc:
            msg = f"config not found: {self._path}"
            raise ConfigError(msg) from exc

        if self._current is None or self._last_mtime != mtime:
            try:
                self._current = load_config(self._path)
                self._last_mtime = mtime
            except ConfigError:
                if self._current is not None:
                    return self._current
                raise

        return self._current
