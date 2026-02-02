import subprocess
import sys
from enum import Enum
from pathlib import Path
from typing import Final

import httpx

FAKE_SERVER_SCRIPT = Path(__file__).resolve().parent.parent / "fakes" / "blog_server.py"


class Scenario(Enum):
    RSS = "rss"
    SITEMAP = "sitemap"
    FULL = "full"


class Mode(Enum):
    BASELINE = "baseline"
    NEW_ARTICLE = "new-article"
    FEED_MOVED = "feed-moved"
    SITEMAP_CHANGED = "sitemap-changed"


_CONTROL_ENDPOINT: Final[str] = "/_control/set-mode"


def start_fake_server(scenario: Scenario) -> tuple[subprocess.Popen[str], int]:
    proc = subprocess.Popen(
        [sys.executable, str(FAKE_SERVER_SCRIPT), "--scenario", scenario.value],
        stdout=subprocess.PIPE,
        text=True,
    )

    if proc.stdout is None:
        msg = "failed to capture stdout from fake server process"
        raise RuntimeError(msg)

    line = proc.stdout.readline().strip()
    port_str = line
    if not port_str.isdigit():
        msg = f"expected port number, got: {line!r}"
        raise RuntimeError(msg)

    return proc, int(port_str)


def set_server_mode(port: int, mode: Mode) -> None:
    response = httpx.post(
        f"http://127.0.0.1:{port}{_CONTROL_ENDPOINT}",
        params={"mode": mode.value},
        timeout=5.0,
    )
    response.raise_for_status()
