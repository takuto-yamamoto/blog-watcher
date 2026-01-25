# ADR-004: Deployment Approach

## Status

Accepted

## Decision

### Dockerfile

```dockerfile
# =============================================================================
# Stage 1: Builder
# =============================================================================
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src/ ./src/
RUN uv sync --frozen --no-dev

# =============================================================================
# Stage 2: Runtime
# =============================================================================
FROM python:3.12-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2 \
    libxslt1.1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 1000 appgroup \
    && useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src

RUN mkdir -p /app/data && chown -R appuser:appgroup /app

USER appuser

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONFAULTHANDLER=1

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

EXPOSE 8080
STOPSIGNAL SIGTERM

ENTRYPOINT ["python", "-m", "blog_watcher"]
CMD ["run"]
```

**Why:**
- **Multi-stage build**: ビルド時依存（gcc, dev headers）をランタイムから除外、イメージサイズ削減
- **Layer caching**: pyproject.toml/uv.lockを先にコピーし、ソース変更時の再ビルドを高速化
- **Non-root user**: コンテナエスケープ時のリスク軽減
- **PYTHONUNBUFFERED=1**: ログがリアルタイム出力（バッファリングなし）

### docker-compose.yaml

```yaml
services:
  blog-watcher:
    build: .
    image: blog-watcher:latest
    container_name: blog-watcher
    restart: unless-stopped
    read_only: true
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges:true
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.5'
    volumes:
      - ./config.toml:/app/config.toml:ro
      - blog-watcher-data:/app/data
      - /tmp
    environment:
      - SLACK_WEBHOOK_URL=${SLACK_WEBHOOK_URL}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
      - TZ=Asia/Tokyo
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s
    ports:
      - "8080:8080"
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
    stop_grace_period: 30s

volumes:
  blog-watcher-data:
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SLACK_WEBHOOK_URL` | Yes | - | Slack Incoming Webhook URL |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `TZ` | No | `UTC` | Timezone |

### Security Hardening

| Item | Implementation | Rationale |
|------|---------------|-----------|
| Non-root user | `USER appuser` | 権限昇格防止 |
| Read-only filesystem | `read_only: true` | ファイル改竄防止 |
| No capabilities | `cap_drop: ALL` | 権限最小化 |
| No privilege escalation | `no-new-privileges:true` | setuid/setgid防止 |
| Resource limits | `memory: 256M` | DoS/メモリリーク影響限定 |

## Design Notes

### Graceful Shutdown

APSchedulerの正常終了処理:

```python
from types import FrameType


class ApplicationLifecycle:
    """Manages application startup and shutdown with signal handling."""

    def __init__(self, scheduler: AsyncIOScheduler, db: Database) -> None:
        self._scheduler = scheduler
        self._db = db
        self._shutdown_event = asyncio.Event()

    def install_signal_handlers(self) -> None:
        """Register signal handlers for graceful shutdown."""
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self._handle_signal, sig)

    def _handle_signal(self, signum: int) -> None:
        """Set shutdown flag without blocking the event loop."""
        logger.info("Received shutdown signal", signal=signal.Signals(signum).name)
        self._shutdown_event.set()

    async def wait_for_shutdown(self) -> None:
        """Block until a shutdown signal is received."""
        await self._shutdown_event.wait()

    async def shutdown(self) -> None:
        """Perform graceful shutdown of all components."""
        logger.info("Starting graceful shutdown")
        self._scheduler.shutdown(wait=True)
        self._db.close()
        logger.info("Shutdown complete")
```

**Why:**

- **SIGTERM + SIGINT**: SIGTERM for Docker, SIGINT for Ctrl+C during development
- **No `sys.exit()` in handler**: Signal handlers should set flags, not perform complex logic. `sys.exit()` can cause issues with async cleanup.
- **Class-based lifecycle**: Avoids global mutable state, improves testability
- **`loop.add_signal_handler`**: Proper async signal handling in event loop context

`stop_grace_period: 30s`で実行中ジョブの完了を待機。データ破損を防止。

### uv sync 2回の意図

```dockerfile
RUN uv sync --frozen --no-dev --no-install-project  # 1回目: 依存のみ
COPY src/ ./src/
RUN uv sync --frozen --no-dev                       # 2回目: プロジェクト自身
```

**Why:**
- 1回目: lxml等のC拡張ビルドを含む重い依存処理をDockerレイヤーキャッシュに固定
- 2回目: アプリコード変更時、依存再ビルドをスキップ（`--no-install-project`で分離したため）

**今後の判断基準:** 依存追加時は1回目が再実行される。ソース変更時は2回目のみ。この分離を崩すとCI/CD時間が大幅増加。

### Named Volume vs Bind Mount

```yaml
volumes:
  - blog-watcher-data:/app/data  # Named volume (推奨)
  # - ./data:/app/data           # Bind mount (非推奨)
```

**Why:**
- SQLite WALは`fsync`/ファイルロック/原子的renameに依存
- Bind mount（特にMac/Windows）ではVMレイヤー経由でPOSIX保証が弱い
- Named volumeはLinux FS上で動作し、SQLiteの期待する挙動を満たす

**今後の判断基準:** 開発時の利便性でbind mountしたい場合、WALモード無効化（`PRAGMA journal_mode=DELETE`）を検討。本番は必ずNamed volume。
