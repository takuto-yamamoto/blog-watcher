# ADR-002: Change Detection Strategy

## Status

Accepted

## Decision

The primary change detection strategy uses HTML content hashing with the following approach:

### HTML Content Hashing Process

1. **Fetch HTML page** via httpx with configurable User-Agent
2. **Extract target content** using CSS selectors (e.g., `main`, `.posts`, `article`)
3. **Exclude dynamic elements** (ads, timestamps, comment counts, sidebars)
4. **Normalize text** (remove extra whitespace)
5. **Compute SHA256 hash** and compare with stored hash
6. **Trigger notification** if hash changed

### Optional: HTTP Headers Pre-check

- HEAD request to check `ETag`/`Last-Modified` before full fetch
- Skip full fetch if headers unchanged (saves bandwidth)
- This feature is planned as a future enhancement

## Context

Blog content changes need to be detected reliably while minimizing false positives from dynamic page elements like advertisements, comment counts, or timestamps.
