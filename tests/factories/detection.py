from __future__ import annotations

from blog_watcher.detection.http_fetcher import FetchResult
from factory.base import Factory

SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Sample Blog</title>
    <link rel="alternate" type="application/rss+xml" href="/feed.xml">
</head>
<body>
    <nav>
        <a href="/about">About</a>
        <a href="/contact">Contact</a>
    </nav>
    <main>
        <article>
            <h1><a href="/posts/article-1">Article 1</a></h1>
            <p>Content</p>
        </article>
        <article>
            <h1><a href="/posts/article-2">Article 2</a></h1>
            <p>Content</p>
        </article>
    </main>
    <footer>
        <a href="/privacy">Privacy</a>
    </footer>
</body>
</html>
"""

SAMPLE_BASE_URL = "https://example.com"


class HtmlFactory(Factory[str]):
    class Meta:
        model = str

    content = SAMPLE_HTML

    @classmethod
    def build(cls, **kwargs: object) -> str:
        content = kwargs.pop("content", cls.content)
        if kwargs:
            msg = "unexpected kwargs"
            raise ValueError(msg)
        return str(content)


class FetchResultFactory(Factory[FetchResult]):
    class Meta:
        model = FetchResult

    status_code = 200
    content = SAMPLE_HTML
    etag = None
    last_modified = None
    is_modified = True
