from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DetectionResult:
    blog_id: str
    changed: bool
    http_status: int | None
    url_fingerprint: str | None
