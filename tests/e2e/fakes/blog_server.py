import argparse
from enum import Enum
from http.server import HTTPServer, SimpleHTTPRequestHandler
from typing import Any, ClassVar, cast
from urllib.parse import parse_qs, urlparse

RSS_HTML = b"""\
<!DOCTYPE html>
<html>
<head>
    <link rel="alternate" type="application/rss+xml" href="/feed.xml">
</head>
</html>
"""

RSS_FEED_BASELINE = b"""\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>Example Blog</title>
        <link>https://example.com</link>
        <description>A sample blog</description>
        <item>
            <title>Article 1</title>
            <link>https://example.com/article-1</link>
            <guid>article-1-guid</guid>
            <pubDate>Mon, 01 Jan 2024 10:00:00 GMT</pubDate>
        </item>
        <item>
            <title>Article 2</title>
            <link>https://example.com/article-2</link>
            <guid>article-2-guid</guid>
            <pubDate>Tue, 02 Jan 2024 10:00:00 GMT</pubDate>
        </item>
    </channel>
</rss>
"""

RSS_FEED_NEW_ARTICLE = b"""\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>Example Blog</title>
        <link>https://example.com</link>
        <description>A sample blog</description>
        <item>
            <title>Article 1</title>
            <link>https://example.com/article-1</link>
            <guid>article-1-guid</guid>
            <pubDate>Mon, 01 Jan 2024 10:00:00 GMT</pubDate>
        </item>
        <item>
            <title>Article 2</title>
            <link>https://example.com/article-2</link>
            <guid>article-2-guid</guid>
            <pubDate>Tue, 02 Jan 2024 10:00:00 GMT</pubDate>
        </item>
        <item>
            <title>Article 3</title>
            <link>https://example.com/article-3</link>
            <guid>article-3-guid</guid>
            <pubDate>Wed, 03 Jan 2024 10:00:00 GMT</pubDate>
        </item>
    </channel>
</rss>
"""


RSS_FEED_MOVED = b"""\
<!DOCTYPE html>
<html>
<head>
    <link rel="alternate" type="application/rss+xml" href="/feed_moved.xml">
</head>
</html>
"""


class Mode(Enum):
    BASELINE = "baseline"
    NEW_ARTICLE = "new-article"
    FEED_MOVED = "feed-moved"
    SITEMAP_CHANGED = "sitemap-changed"


def _build_rss_routes(mode: Mode) -> dict[str, tuple[str, bytes]]:
    match mode:
        case Mode.BASELINE:
            return {
                "/": ("text/html", RSS_HTML),
                "/feed.xml": ("application/rss+xml", RSS_FEED_BASELINE),
            }
        case Mode.NEW_ARTICLE:
            return {
                "/": ("text/html", RSS_HTML),
                "/feed.xml": ("application/rss+xml", RSS_FEED_NEW_ARTICLE),
            }
        case Mode.FEED_MOVED:
            return {
                "/": ("text/html", RSS_FEED_MOVED),
                "/feed_moved.xml": ("application/rss+xml", RSS_FEED_BASELINE),
            }
        case _:
            msg = f"unsupported mode for rss scenario: {mode}"
            raise ValueError(msg)


def _build_sitemap_routes(port: int, mode: Mode) -> dict[str, tuple[str, bytes]]:
    base = f"http://127.0.0.1:{port}"
    urls = [
        f"{base}/posts/hello-world",
        f"{base}/posts/second-post",
    ]

    if mode is Mode.NEW_ARTICLE:
        urls.append(f"{base}/posts/third-post")

    url_entries = "".join(f"  <url><loc>{u}</loc></url>\n" for u in urls)

    sitemap_xml = f"""\
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{url_entries}
</urlset>
""".encode()

    match mode:
        case Mode.BASELINE | Mode.NEW_ARTICLE:
            robots_txt = f"Sitemap: {base}/sitemap.xml\n".encode()
            return {
                "/": ("text/html", b"<html><body>no feed</body></html>"),
                "/robots.txt": ("text/plain", robots_txt),
                "/sitemap.xml": ("application/xml", sitemap_xml),
            }
        case Mode.FEED_MOVED:
            robots_txt = f"Sitemap: {base}/sitemap_moved.xml\n".encode()
            return {
                "/": ("text/html", b"<html><body>no feed</body></html>"),
                "/robots.txt": ("text/plain", robots_txt),
                "/sitemap_moved.xml": ("application/xml", sitemap_xml),
            }
        case _:
            msg = f"unsupported mode for sitemap scenario: {mode}"
            raise ValueError(msg)


def _build_full_routes(port: int, mode: Mode) -> dict[str, tuple[str, bytes]]:
    base = f"http://127.0.0.1:{port}"
    urls = [
        f"{base}/posts/hello-world",
        f"{base}/posts/second-post",
    ]

    if mode is Mode.SITEMAP_CHANGED:
        urls.append(f"{base}/posts/third-post")

    url_entries = "".join(f"  <url><loc>{u}</loc></url>\n" for u in urls)

    sitemap_xml = f"""\
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{url_entries}
</urlset>
""".encode()

    robots_txt = f"Sitemap: {base}/sitemap.xml\n".encode()

    return {
        "/": ("text/html", RSS_HTML),
        "/feed.xml": ("application/rss+xml", RSS_FEED_BASELINE),
        "/robots.txt": ("text/plain", robots_txt),
        "/sitemap.xml": ("application/xml", sitemap_xml),
    }


class Handler(SimpleHTTPRequestHandler):
    _routes: ClassVar[dict[str, tuple[str, bytes]]] = {}
    _mode: ClassVar[Mode] = Mode.BASELINE
    _scenario: ClassVar[str] = "rss"

    @classmethod
    def _build_routes(cls, mode: Mode, port: int) -> dict[str, tuple[str, bytes]]:
        if cls._scenario == "rss":
            return _build_rss_routes(mode)
        if cls._scenario == "full":
            return _build_full_routes(port, mode)
        return _build_sitemap_routes(port, mode)

    @classmethod
    def configure(cls, *, scenario: str, port: int) -> None:
        cls._scenario = scenario
        cls._routes = cls._build_routes(cls._mode, port)

    @classmethod
    def set_mode(cls, *, mode: Mode, port: int) -> None:
        cls._mode = mode
        cls._routes = cls._build_routes(mode, port)

    def do_GET(self) -> None:
        route = self._routes.get(self.path)

        if route is None:
            self.send_error(404)
            return

        content_type, body = route
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/_control/set-mode":
            self.send_error(404)
            return

        params = parse_qs(parsed.query)
        mode_raw = params.get("mode", [None])[0]

        try:
            mode = Mode(mode_raw)
        except ValueError:
            self.send_error(400)
            return

        addr = cast("tuple[Any, ...]", self.server.server_address)
        self.set_mode(mode=mode, port=int(addr[1]))
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", choices=["rss", "sitemap", "full"], default="rss")
    args = parser.parse_args()

    server = HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]

    Handler.configure(scenario=args.scenario, port=port)

    print(port, flush=True)  # noqa: T201 — stdout is the IPC channel to the test harness
    server.serve_forever()


if __name__ == "__main__":
    main()
