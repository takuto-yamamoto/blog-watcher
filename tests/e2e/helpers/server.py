import subprocess
import sys
from enum import Enum
from pathlib import Path

FAKE_SERVER_SCRIPT = Path(__file__).resolve().parent.parent / "fakes" / "blog_server.py"


class Scenario(Enum):
    RSS = "rss"
    SITEMAP = "sitemap"


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
