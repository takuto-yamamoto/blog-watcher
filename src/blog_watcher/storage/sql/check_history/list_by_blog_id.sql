SELECT blog_id, checked_at, http_status, skipped, changed,
       url_fingerprint, error_message
FROM check_history
WHERE blog_id = ?
ORDER BY checked_at DESC;
