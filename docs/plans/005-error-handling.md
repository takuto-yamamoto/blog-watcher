# ADR-005: Error Handling Strategy

## Status

Accepted

## Decision

### Error Categories

| Category | Examples | Action |
|----------|----------|--------|
| **Transient** | Timeout, 5xx, DNS failure | リトライ（exponential backoff） |
| **Permanent** | 404, 410 Gone | ログ出力、通知、ブログを無効化検討 |
| **Rate Limit** | 429 Too Many Requests | Retry-Afterヘッダーに従う、なければ長めのbackoff |
| **Config Error** | Invalid URL, selector | 起動時にfail-fast |

### Retry Policy

```python
from tenacity import (
    retry,
    retry_if_exception,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

# Retryable exception types in httpx
# Note: httpx.NetworkError does not exist; use ConnectError for connection failures
RETRYABLE_EXCEPTIONS = (
    httpx.TimeoutException,  # Read/write/connect timeout
    httpx.ConnectError,      # Connection refused, DNS failure, etc.
)


def _is_retryable_status_error(exc: BaseException) -> bool:
    """Return True if exception is an HTTPStatusError with 5xx status."""
    return (
        isinstance(exc, httpx.HTTPStatusError)
        and exc.response.status_code >= 500
    )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=(
        retry_if_exception_type(RETRYABLE_EXCEPTIONS)
        | retry_if_exception(_is_retryable_status_error)
    ),
    before_sleep=before_sleep_log(logger, logging.WARNING),
)
async def fetch_with_retry(client: httpx.AsyncClient, url: str) -> httpx.Response:
    """Fetch URL with automatic retry on transient errors."""
    response = await client.get(url)
    if response.status_code >= 500:
        raise httpx.HTTPStatusError(
            f"Server error {response.status_code}",
            request=response.request,
            response=response,
        )
    return response
```

**Why:**

- 最大3回リトライ
- 指数バックオフ（2s → 4s → 8s... 最大30s）
- `httpx.ConnectError` for connection failures (not `NetworkError` which does not exist)
- 5xx errors are retryable via `HTTPStatusError` check (server may recover)
- 4xx errors are NOT retried (client-side issue, won't fix itself)
- Async-first to match project's async architecture (ADR-006)

### 429 Rate Limit Handling

```python
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

# Maximum wait time to prevent DoS via malicious Retry-After header
MAX_RETRY_AFTER_SECONDS = 3600  # 1 hour


def parse_retry_after(header_value: str | None, default: int = 60) -> int:
    """
    Parse Retry-After header value.

    Supports both formats per RFC 7231:
    - Seconds: "120" (wait 120 seconds)
    - HTTP-date: "Wed, 21 Oct 2015 07:28:00 GMT"

    Returns seconds to wait, capped at MAX_RETRY_AFTER_SECONDS.
    """
    if header_value is None:
        return default

    # Try parsing as integer (seconds)
    try:
        seconds = int(header_value)
        return min(seconds, MAX_RETRY_AFTER_SECONDS)
    except ValueError:
        pass

    # Try parsing as HTTP-date
    try:
        retry_at = parsedate_to_datetime(header_value)
        now = datetime.now(timezone.utc)
        seconds = max(0, int((retry_at - now).total_seconds()))
        return min(seconds, MAX_RETRY_AFTER_SECONDS)
    except (ValueError, TypeError):
        return default


async def handle_rate_limit(response: httpx.Response) -> None:
    """Handle 429 response by waiting according to Retry-After header."""
    retry_after = parse_retry_after(response.headers.get("Retry-After"))
    logger.warning(
        "Rate limited by server",
        url=str(response.url),
        retry_after_seconds=retry_after,
    )
    await asyncio.sleep(retry_after)  # Non-blocking sleep in async context
```

**Why:**

- **HTTP-date parsing**: RFC 7231 allows both seconds and date formats
- **Capped wait time**: Prevents malicious servers from causing DoS via huge Retry-After values
- **`asyncio.sleep`**: Non-blocking; allows other tasks to run during wait

### Permanent Error Handling

404/410が連続N回発生した場合:
1. Slackに警告通知
2. `blog_state.consecutive_errors` をインクリメント
3. 閾値超過でログに警告（自動無効化はしない、手動対応）

**Why:** 一時的な404（デプロイ中等）もあるため、即座に無効化しない。

### Notification Failure

Slack通知失敗時:
1. リトライ（最大2回）
2. 失敗してもブログチェック処理は継続
3. エラーログに記録

**Why:** 通知失敗でメインの監視処理を止めない。

### Health Check Endpoint

`/health` エンドポイント（Docker health check用）:

```python
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class HealthStatus(StrEnum):
    """Health check status values."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"


@dataclass(frozen=True, slots=True)
class HealthCheckResult:
    """Structured health check response."""

    status: HealthStatus
    checks: dict[str, bool]

    def to_dict(self) -> dict[str, object]:
        return {"status": self.status, "checks": self.checks}


class SchedulerProtocol(Protocol):
    """Protocol for scheduler health check."""

    @property
    def running(self) -> bool: ...


class DatabaseProtocol(Protocol):
    """Protocol for database health check."""

    def execute(self, query: str) -> object: ...


class HealthChecker:
    """
    Health checker with dependency injection.

    Usage:
        checker = HealthChecker(db=db, scheduler=scheduler)
        result = checker.check()
    """

    def __init__(
        self,
        db: DatabaseProtocol,
        scheduler: SchedulerProtocol,
    ) -> None:
        self._db = db
        self._scheduler = scheduler

    def check(self) -> HealthCheckResult:
        """
        Perform health checks on all components.

        Returns structured result; never exposes internal error details.
        """
        checks: dict[str, bool] = {}

        # Database check
        try:
            self._db.execute("SELECT 1")
            checks["database"] = True
        except Exception:
            # Log internally, but don't expose error message (may leak paths/credentials)
            logger.exception("Database health check failed")
            checks["database"] = False

        # Scheduler check
        checks["scheduler"] = self._scheduler.running

        status = (
            HealthStatus.HEALTHY
            if all(checks.values())
            else HealthStatus.UNHEALTHY
        )
        return HealthCheckResult(status=status, checks=checks)


# HTTP handler example (aiohttp)
async def health_handler(request: web.Request) -> web.Response:
    """Health check endpoint handler."""
    checker: HealthChecker = request.app["health_checker"]
    result = checker.check()
    status_code = 200 if result.status == HealthStatus.HEALTHY else 503
    return web.json_response(result.to_dict(), status=status_code)
```

**Why:**

- **Dependency injection**: `HealthChecker` receives dependencies in constructor, no globals
- **Protocol types**: Enables type-safe mocking in tests
- **Structured response**: Returns JSON with per-component status, not bare strings
- **No exception leakage**: Errors are logged internally, but never returned in response (prevents credential/path leakage)

## Context

外部HTTPリクエストを行うアプリケーションでは、ネットワーク障害、サーバー障害、レート制限など様々なエラーが発生する。適切なエラー分類とリトライ戦略により、一時的な障害からの自動回復と永続的な問題の早期検出を両立する。
