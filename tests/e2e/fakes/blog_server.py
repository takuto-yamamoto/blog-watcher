from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures"


def _read_fixture(name: str) -> bytes:
    return (FIXTURES_DIR / name).read_bytes()


ROUTES: dict[str, tuple[str, bytes]] = {
    "/": ("text/html", _read_fixture("html/feed_link_rss.html")),
    "/feed.xml": ("application/rss+xml", _read_fixture("feeds/rss_valid.xml")),
}


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self) -> None:
        route = ROUTES.get(self.path)

        if route is None:
            self.send_error(404)
            return

        content_type, body = route
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    server = HTTPServer(("127.0.0.1", 0), Handler)
    print(server.server_address[1], flush=True)  # noqa: T201 — stdout is the IPC channel to the test harness
    server.serve_forever()


if __name__ == "__main__":
    main()
