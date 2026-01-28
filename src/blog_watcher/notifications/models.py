from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Notification:
    title: str
    body: str
    url: str | None = None
