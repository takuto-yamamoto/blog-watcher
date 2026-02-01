import subprocess
import sys
from pathlib import Path

E2E_ROOT = Path(__file__).resolve().parent.parent
FAKE_SERVER_SCRIPT = E2E_ROOT / "fakes" / "blog_server.py"


def start_fake_server() -> tuple[subprocess.Popen[str], int]:
    proc = subprocess.Popen(
        [sys.executable, str(FAKE_SERVER_SCRIPT)],
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
