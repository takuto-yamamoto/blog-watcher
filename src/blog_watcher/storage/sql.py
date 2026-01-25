SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS blog_state (
    blog_id TEXT PRIMARY KEY,
    etag TEXT,
    last_modified TEXT,
    url_fingerprint TEXT,
    feed_url TEXT,
    sitemap_url TEXT,
    recent_entry_keys TEXT,
    last_checked_at TEXT NOT NULL,
    last_changed_at TEXT,
    consecutive_errors INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS check_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    blog_id TEXT NOT NULL,
    checked_at TEXT NOT NULL,
    http_status INTEGER,
    skipped INTEGER NOT NULL DEFAULT 0,
    changed INTEGER NOT NULL DEFAULT 0,
    url_fingerprint TEXT,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_check_history_blog_time
ON check_history(blog_id, checked_at DESC);

CREATE INDEX IF NOT EXISTS idx_check_history_changed
ON check_history(changed) WHERE changed = 1;
"""
