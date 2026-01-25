INSERT INTO check_history (
    blog_id,
    checked_at,
    http_status,
    skipped,
    changed,
    url_fingerprint,
    error_message
) VALUES (?, ?, ?, ?, ?, ?, ?);
