from __future__ import annotations

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
