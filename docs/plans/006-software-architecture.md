# ADR-006: ソフトウェアアーキテクチャ

## ステータス

提案中

## コンテキスト

プロジェクト構成（`src/blog_watcher/{config,core,detection,notifications,storage}/`）は存在するが、責務・相互作用パターン・設計原則が文書化されていない。本ADRは、技術選定（ADR-001）、ストレージ設計（ADR-003）、エラーハンドリング戦略（ADR-005）を補完するソフトウェアアーキテクチャの決定事項を定める。

本ADRが扱う主な問い:
1. 各モジュールの責務は何か?
2. 依存関係はどのように接続すべきか?
3. コードベースは同期・非同期・ハイブリッドのどれか?
4. データベースアクセスはどう抽象化するか?

---

## 決定

### 1. モジュール構成と責務

#### モジュール依存グラフ

```
┌────────────┐
│   config   │  ← 純粋なデータモデル、他モジュールに依存しない
└────────────┘
       ↓
┌────────────┐
│  storage   │  ← config（DTO）にのみ依存
└────────────┘
       ↓
┌────────────┐     ┌────────────┐
│ detection  │     │notifications│  ← 両者とも storage/config に依存
└────────────┘     └────────────┘
       ↓                 ↓
       └────────┬────────┘
                ↓
         ┌────────────┐
         │    core    │  ← detection + notifications をオーケストレーション
         └────────────┘
                ↓
         ┌────────────┐
         │    main    │  ← 依存関係の組み立て、CLI提供
         └────────────┘
```

#### モジュールの責務

| モジュール | 責務 | 依存可能なモジュール |
|--------|---------------|---------------|
| `config/` | 設定スキーマの定義、TOML読み込み、環境変数のマージ | なし（末端モジュール） |
| `storage/` | DB接続、スキーマ管理、CRUD操作 | `config` |
| `detection/` | HTTP取得、フィード/サイトマップ検出、URL正規化、変更検知 | `config`, `storage` |
| `notifications/` | 通知インターフェースの抽象化、Slack実装 | `config` |
| `core/` | BlogWatcherのオーケストレーション、APScheduler統合、ヘルスサーバ | 全モジュール |
| `main.py` | CLI定義、依存関係の組み立て、アプリケーションライフサイクル | 全モジュール |

**この構成の理由:**
- **循環しない依存関係**: 各モジュールはグラフ上の「上位」モジュールにのみ依存し、循環参照を防ぎテストを簡潔化。
- **単一責任**: `detection` は通知を知らず、`notifications` は検知を知らない。両者を結び付けるのは `core` のみ。
- **テスタビリティ**: 下位モジュールは上位のモックなしで単体テスト可能。

**トレードオフ:**
- (+) 境界が明確でオンボーディングしやすい
- (+) 複雑なフィクスチャなしでモジュール単体をテスト可能
- (-) 一部の間接化（例: `detection` が直接通知せず `core.watcher` が調整）
- (-) 相互依存を避けるための規律が必要

---

### 2. 依存性注入アプローチ

**決定: ファクトリ関数パターン（DIフレームワークなし）**

```python
# main.py
from contextlib import contextmanager
from dataclasses import dataclass
from collections.abc import Generator


@dataclass(frozen=True, slots=True)
class ApplicationComponents:
    """Container for application dependencies with typed access."""

    config: AppConfig
    db: Database
    watcher: BlogWatcher
    scheduler: WatcherScheduler


@contextmanager
def create_application(config_path: Path) -> Generator[ApplicationComponents, None, None]:
    """
    Create and manage application components with proper lifecycle.

    Usage:
        with create_application(Path("config.toml")) as app:
            app.scheduler.start()
            await lifecycle.wait_for_shutdown()

    Guarantees cleanup even on partial initialization failure.
    """
    db: Database | None = None
    try:
        config = load_config(config_path)

        # Storage layer
        db = Database(Path(config.storage.database_path))
        db.initialize()
        state_repo = BlogStateRepository(db)
        history_repo = CheckHistoryRepository(db)

        # Detection layer
        fetcher = HttpFetcher(
            user_agent=config.http.user_agent,
            connect_timeout=config.http.connect_timeout,
            read_timeout=config.http.read_timeout,
        )
        feed_detector = FeedDetector(fetcher, state_repo)
        sitemap_detector = SitemapDetector(fetcher, state_repo)
        html_detector = HtmlUrlDetector(fetcher, state_repo)
        detector = ChangeDetector(
            feed_detector,
            sitemap_detector,
            html_detector,
            history_repo,
        )

        # Notification layer
        notifier = SlackNotifier(config.slack)

        # Core layer
        watcher = BlogWatcher(config, detector, notifier)
        scheduler = WatcherScheduler(config, watcher)

        yield ApplicationComponents(
            config=config,
            db=db,
            watcher=watcher,
            scheduler=scheduler,
        )
    finally:
        # Cleanup resources in reverse order of creation
        if db is not None:
            db.close()
```

**理由:**
- **シンプル**: コンポーネントの接続を1箇所で理解できる
- **明示的**: 登録や自動配線の「魔法」がない
- **型安全**: IDE支援が効き、mypyでコンストラクタの署名を検証可能
- **追加依存なし**: `dependency-injector` や `inject` を不要にする

**検討した代替案:**

| アプローチ | Pros | Cons | 決定 |
|----------|------|------|----------|
| **ファクトリ関数** | シンプルで明示的、依存なし | 大規模アプリでは冗長 | ✓ 採用 |
| **DIコンテナ（dependency-injector）** | 宣言的、遅延生成 | 学習コスト、実行時エラー | 不採用 |
| **Service Locator** | 柔軟 | 依存が隠れる、テストしづらい | 不採用 |
| **グローバルシングルトン** | 便利 | テスト困難、暗黙状態 | 不採用 |

**将来の検討:** アプリが大きくなり（10+サービスでライフサイクルが複雑化）したらDIコンテナを再検討する。MVPではファクトリ関数で十分。

---

### 3. Async vs Sync 実行モデル

**決定: 非同期優先 + 同期DBアクセス**

| コンポーネント | 実行モデル | 理由 |
|-----------|----------------|-----------|
| HTTP Fetcher | **Async** | ネットワークI/Oで複数ブログを並列チェック可能 |
| Slack Notifier | **Async** | ネットワークI/Oでノンブロッキング |
| BlogWatcher | **Async** | 非同期処理のオーケストレーション |
| Scheduler | **Async** | APSchedulerの `AsyncIOScheduler` を使いイベントループ統合 |
| Health Server | **Async** | aiohttpの軽量サーバ |
| SQLite Repository | **Sync** | 下記理由参照 |

**SQLiteを同期にする理由:**

1. **stdlib sqlite3は同期専用**: Python標準の `sqlite3` は `async`/`await` をサポートしない。非同期コードで使うには `run_in_executor()` が必要。

2. **aiosqliteの実益が小さい**: `aiosqlite` は同期呼び出しをスレッドプールに包むだけ。ローカルファイルI/Oでは複雑さの割に性能向上が小さい。

3. **SQLite操作は高速**: DB操作はローカルディスクI/O（単純クエリは通常 <1ms）で、イベントループを短時間ブロックしても許容範囲。

4. **単一書き込みの性質**: SQLiteは書き込みを直列化するため、asyncでも同時書き込みは実現しない。

**トレードオフ:**
- (+) async DB用の追加依存が不要
- (+) 非同期アプリに同期DBというシンプルなモデル
- (-) DB書き込み中にメインスレッドがブロック（操作が短い前提）
- (-) DB操作が遅い場合は `run_in_executor` ラッパーが必要

**エスケープハッチ:** プロファイルでDBブロッキングが問題化した場合:

```python
from concurrent.futures import ThreadPoolExecutor

# Shared executor for DB operations (single thread to preserve SQLite's serial semantics)
_db_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="db-")


async def get_state_async(
    repo: BlogStateRepository,
    blog_id: str,
) -> BlogState | None:
    """
    Run sync DB operation in a thread pool to avoid blocking the event loop.

    Uses get_running_loop() (Python 3.10+) instead of deprecated get_event_loop().
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_db_executor, repo.get, blog_id)
```

**注記:**

- `asyncio.get_running_loop()` はPython 3.10+で正しいAPI（3.12+で必須）
- `asyncio.get_event_loop()` は非推奨で、Python 3.12では `DeprecationWarning` を出す
- 返り値の型は `BlogState | None`（`repo.get()` が `None` を返すため）
- 共有の単一スレッドExecutorでSQLiteの直列書き込みの性質を保つ

---

### 4. リポジトリパターン

**決定: プレーンなデータクラスでリポジトリパターンを採用**

```python
# storage/models.py (DTOs)
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class BlogState:
    """
    Immutable state snapshot for a blog.

    Using frozen=True for:
    - Thread safety (no accidental mutation)
    - Hashable (can use as dict key or in sets)
    - Clear intent: state is a value object, not mutable entity

    Using slots=True for:
    - Memory efficiency (no __dict__)
    - Faster attribute access
    """

    blog_id: str
    etag: str | None
    last_modified: str | None
    url_fingerprint: str | None
    last_check_at: datetime
    last_change_at: datetime | None
    consecutive_errors: int = 0

    def __post_init__(self) -> None:
        """Validate invariants after initialization."""
        if not self.blog_id:
            raise ValueError("blog_id cannot be empty")
        if self.consecutive_errors < 0:
            raise ValueError("consecutive_errors cannot be negative")


# storage/repository.py
class BlogStateRepositoryProtocol(Protocol):
    """Protocol for blog state persistence operations."""

    def get(self, blog_id: str) -> BlogState | None: ...
    def upsert(self, state: BlogState) -> None: ...
    def delete(self, blog_id: str) -> bool: ...
    def list_all(self) -> list[BlogState]: ...


class BlogStateRepository:
    """SQLite implementation of BlogStateRepositoryProtocol."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def get(self, blog_id: str) -> BlogState | None:
        row = self._db.execute(
            "SELECT * FROM blog_state WHERE blog_id = ?", (blog_id,)
        ).fetchone()
        return self._row_to_state(row) if row else None

    def upsert(self, state: BlogState) -> None: ...
    def delete(self, blog_id: str) -> bool: ...
    def list_all(self) -> list[BlogState]: ...

    def _row_to_state(self, row: sqlite3.Row) -> BlogState:
        """Map database row to BlogState dataclass."""
        return BlogState(
            blog_id=row["blog_id"],
            etag=row["etag"],
            last_modified=row["last_modified"],
            url_fingerprint=row["url_fingerprint"],
            last_check_at=datetime.fromisoformat(row["last_check_at"]),
            last_change_at=(
                datetime.fromisoformat(row["last_change_at"])
                if row["last_change_at"]
                else None
            ),
            consecutive_errors=row["consecutive_errors"],
        )
```

**リポジトリパターンを採用する理由:**

1. **テスタビリティ**: Detectorテストで `BlogStateRepository` をモックでき、SQLiteに触れずに済む
2. **SQLの分離**: SQLクエリは1箇所に集約し、ビジネスロジックと混在させない
3. **抽象化**: ストレージが変わっても（可能性は低いが）リポジトリのみ変更で済む

**ORMを使わない理由（SQLAlchemy, Peewee）:**

1. **オーバーヘッド**: 2つのテーブルのためにORMは過剰
2. **学習コスト**: SQLに加えてORMの作法が必要
3. **性能**: 単純操作では sqlite3 の方が速い
4. **制御性**: 生SQLでクエリ最適化を完全に制御できる

**トレードオフ:**
- (+) データアクセスの分離が明確
- (+) テストでのモックが容易
- (+) SQLを直接制御できる
- (-) 行 -> オブジェクト変換が手作業でボイラープレート
- (-) ORMの利便性（自動マイグレーション等）がない

---

### 5. 設定の伝播

**決定: サービスに最小限の設定を渡す**

```python
# Good: Service receives only what it needs
class HttpFetcher:
    def __init__(self, user_agent: str, connect_timeout: float, read_timeout: float):
        ...

# Avoid: Service receives entire config
class HttpFetcher:
    def __init__(self, config: AppConfig):  # Knows too much
        ...
```

**理由:**
- **インターフェース分離**: コンポーネントは必要な情報だけを見る
- **依存の明示**: コンストラクタのシグネチャが要件を明確に示す
- **テスタビリティ**: テスト値で容易に生成できる

**例外:** `BlogWatcher` はオーケストレーションのためにブログ一覧が必要なので `AppConfig` を受け取ってよい。

---

## 結果

### ポジティブ
- 明確なモジュール境界で並行開発が可能
- ファクトリ関数DIは理解・デバッグが容易
- 非同期HTTPでマルチブログの同時チェックを最大化
- リポジトリパターンでストレージ実装詳細を隔離

### ネガティブ
- サービス増加に伴いファクトリ関数が冗長化
- 非同期アプリで同期DBを使うため高速性への規律が必要
- データクラスの手作業マッピングがボイラープレート

### リスク
- アーキテクチャ原則が守られないとモジュール間依存が侵入
- 性能: 1回のブログチェックが長引くと他のジョブが遅延（APSchedulerの `max_instances` で緩和）

---

## 将来の開発メモ

1. **Web UI追加**: ダッシュボードを追加する場合は `web/` モジュールと専用APIレイヤを検討
2. **通知チャネルの追加**: 抽象 `Notifier` によりDiscordやEmail等を追加可能
3. **メトリクス**: ヘルスサーバに `/metrics` エンドポイントでPrometheus連携を追加
4. **コンテンツ差分**: `detection/` に追加しても他モジュールに影響しない
