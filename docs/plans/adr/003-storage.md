# ADR-003: Storage Solution

## Status

Accepted

## Decision

SQLite will be used as the storage solution with the following schema:

### Database Tables

1. **blogs** - Blog configuration and metadata
2. **blog_state** - Current state of each monitored blog (hash values, last check time)
3. **check_history** - Historical record of all checks performed

## Context

The application requires persistent storage for blog configurations, current state tracking, and historical check records. SQLite provides built-in support, zero-configuration setup, and adequate performance for concurrent access in a single-instance deployment model.
