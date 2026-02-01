import argparse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from typing import ClassVar

RSS_HTML = b"""\
<!DOCTYPE html>
<html>
<head>
    <link rel="alternate" type="application/rss+xml" href="/feed.xml">
</head>
</html>
"""

RSS_FEED = b"""\
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


def _build_rss_routes() -> dict[str, tuple[str, bytes]]:
    return {
        "/": ("text/html", RSS_HTML),
        "/feed.xml": ("application/rss+xml", RSS_FEED),
    }


def _build_sitemap_routes(port: int) -> dict[str, tuple[str, bytes]]:
    base = f"http://127.0.0.1:{port}"
    robots_txt = f"Sitemap: {base}/sitemap.xml\n".encode()
    sitemap_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <url><loc>{base}/posts/hello-world</loc></url>\n"
        f"  <url><loc>{base}/posts/second-post</loc></url>\n"
        "</urlset>\n"
    ).encode()
    return {
        "/": ("text/html", b"<html><body>no feed</body></html>"),
        "/robots.txt": ("text/plain", robots_txt),
        "/sitemap.xml": ("application/xml", sitemap_xml),
    }


class Handler(SimpleHTTPRequestHandler):
    _routes: ClassVar[dict[str, tuple[str, bytes]]] = {}

    @classmethod
    def set_routes(cls, routes: dict[str, tuple[str, bytes]]) -> None:
        cls._routes = routes

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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", choices=["rss", "sitemap"], default="rss")
    args = parser.parse_args()

    server = HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]

    Handler.set_routes(_build_rss_routes() if args.scenario == "rss" else _build_sitemap_routes(port))

    print(port, flush=True)  # noqa: T201 — stdout is the IPC channel to the test harness
    server.serve_forever()


if __name__ == "__main__":
    main()
