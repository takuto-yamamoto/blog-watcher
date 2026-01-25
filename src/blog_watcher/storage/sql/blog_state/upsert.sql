INSERT INTO blog_state (
    blog_id,
    etag,
    last_modified,
    url_fingerprint,
    feed_url,
    sitemap_url,
    recent_entry_keys,
    last_checked_at,
    last_changed_at,
    consecutive_errors
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(blog_id) DO UPDATE SET
    etag=excluded.etag,
    last_modified=excluded.last_modified,
    url_fingerprint=excluded.url_fingerprint,
    feed_url=excluded.feed_url,
    sitemap_url=excluded.sitemap_url,
    recent_entry_keys=excluded.recent_entry_keys,
    last_checked_at=excluded.last_checked_at,
    last_changed_at=excluded.last_changed_at,
    consecutive_errors=excluded.consecutive_errors;
