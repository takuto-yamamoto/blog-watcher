# ADR-007: テスト戦略

## ステータス

Proposed

## コンテキスト

blog-watcherアプリケーションには、非同期HTTP操作、SQLite永続化、コンテンツ変更検知、通知配信の信頼性を担保する包括的なテスト戦略が必要。テスタビリティに影響する主な設計決定は以下の通り:

- **非同期優先設計**（ADR-006）: HTTP取得とスケジューリングは非同期; SQLiteは同期
- **リポジトリパターン**（ADR-006）: データアクセスをプロトコルベースのインターフェースで抽象化
- **ファクトリ関数DI**（ADR-006）: DIフレームワーク無し; 明示的なコンストラクタ注入でモックが容易
- **リトライを含むエラーハンドリング**（ADR-005）: Tenacityベースのリトライに失敗シナリオのテストが必要
- **URL差分検知パイプライン**（ADR-002）: URL抽出 → 正規化 → 指紋化（ハッシュ化）は決定的なテストデータが必要

本ADRは、テスト標準、ツール選定、TDDワークフロー規律を定める。

---

## 決定

### 1. テストピラミッドとカバレッジ目標

#### テストの分布

| テストレベル | 割合 | カバレッジ目標 | 実行時間 |
|------------|------|---------------|---------|
| **ユニットテスト** | 70% | 行カバレッジ 90%+ | 合計 <10s |
| **統合テスト** | 25% | 重要経路 | 合計 <30s |
| **E2Eテスト** | 5% | スモークテストのみ | 合計 <60s |

```
        /\
       /  \  E2E (5%)
      /----\  - 全体ライフサイクル
     /      \  - Dockerコンテナのヘルスチェック
    /--------\  統合テスト (25%)
   /          \  - SQLiteリポジトリ操作
  /            \  - モックサーバを使うHTTPクライアント
 /--------------\  - スケジューラジョブの実行
/                \ ユニットテスト (70%)
------------------  - 純粋関数（正規化、指紋化、パース）
                    - プロトコルベースのモック注入
                    - エラーハンドリング分岐
```

**この分布の理由:**

- **ユニットテスト (70%)**: 主要ロジックは純粋関数（URL抽出、正規化、指紋化、config検証）に集中。高速・決定的でROIが高い。
- **統合テスト (25%)**: リポジトリパターンのため、SQL正当性を確認するSQLite統合テストが必要。HTTPクライアントは実際のレスポンス処理を検証するためモックサーバを利用。
- **E2Eテスト (5%)**: CLI起動で設定ファイル入力からDB/Slack/ログまで最小パスを通す。SlackはBot APIで最新5件から送信確認。フルE2Eは高コストかつ脆い。

#### カバレッジ要件

| モジュール | 最低カバレッジ | 理由 |
|--------|--------------|------|
| `config/` | 95% | 設定エラーは早期に検知する必要があるため全検証経路をテスト |
| `storage/` | 90% | CRUD操作が重要; SQL正当性を検証 |
| `detection/` | 90% | コアロジック; 変更検知の精度が最重要 |
| `notifications/` | 85% | 外部依存; インターフェース準拠に集中 |
| `core/` | 80% | オーケストレーション; 一部は単体テストが困難 |
| `main.py` | 70% | CLI配線; 統合寄り |

**全体目標:** 行カバレッジ 85%、分岐カバレッジ 80%

---

### 2. テストフレームワーク選定

#### コアフレームワーク

依存関係は `pyproject.toml` の `[dependency-groups.dev]` に定義。

| ツール | 目的 | 検討した代替 |
|-------|------|-------------|
| `pytest` | テストフレームワーク | unittest - 冗長 |
| `pytest-asyncio` | 非同期テストのネイティブ対応 | anyio - 設定が複雑 |
| `pytest-cov` | カバレッジ計測 | coverage.py直接 - 統合性が低い |
| `respx` | httpx向けのパターンマッチングモック | responses - requests専用 |
| `pytest-httpserver` | 統合テスト用の実HTTPサーバ | aiohttp テストサーバ - APIが異なる |
| `freezegun` | スケジューラ用の時間固定 | time-machine - 類似だが成熟度が低い |
| `factory-boy` | 型付きのテストデータ生成 | faker - モデル連携なし |
| `pytest-randomly` | テスト順依存を検出 | 手動シード管理 - エラーを起こしやすい |

---

### 3. モジュール別テストケースマトリックス

本セクションは各モジュールの包括的なテストシナリオを定義する。

#### 3.1 `config/` モジュール

**ユニットテスト（TDDフェーズ別）:**

**Phase 1: TDD初期（RED/GREENの核）**

| テストケース | シナリオ | 期待結果 |
|------------|---------|---------|
| `test_load_valid_config_returns_app_config` | 全必須フィールドを含む有効なTOML | AppConfigへのパース成功 |
| `test_missing_required_field_raises_error` | `slack.webhook_url` が未設定 | 説明的な検証エラー |
| `test_load_invalid_url_raises_validation_error` | 不正なURLを持つブログ | 該当ブログを特定するValueError |

**Phase 2: 安全網の拡張（リファクタ前に追加）**

| テストケース | シナリオ | 期待結果 |
|------------|---------|---------|
| `test_load_empty_blogs_raises_validation_error` | 空のblogs配列 | 明確なメッセージでValueError |
| `test_invalid_toml_raises_error` | 無効なTOML構文 | 構文エラーの例外 |
| `test_type_mismatch_raises_validation_error` | 型の不一致 | 検証エラー |
| `test_env_var_overrides_slack_webhook_url` | `SLACK_WEBHOOK_URL` が設定されている | TOMLの値を上書きして読み込む |

**統合テスト:** なし（純粋な検証ロジック）

**最適化指針:**
- 欠落フィールド/型不一致は `@pytest.mark.parametrize` で集約
- URL検証もパラメータ化して失敗原因を明示
- パス展開は仕様確定後に追加

#### 3.2 `storage/` モジュール

**ユニットテスト:** なし（リポジトリパターンは実DBが必要）

**統合テスト（TDDフェーズ別）:**

**Phase 1: TDD初期（核となるCRUD契約の固定）**

| テストケース | シナリオ | 期待結果 |
|------------|---------|---------|
| `test_upsert_and_get_round_trip` | 状態を保存して取得 | 同一オブジェクトが返る |
| `test_get_nonexistent_returns_none` | 存在しないblog_idをクエリ | 例外ではなくNoneを返す |
| `test_upsert_updates_existing_record` | 同一blog_idで2回upsert | 2回目は更新（重複なし） |
| `test_history_query_orders_by_timestamp` | 複数のチェック履歴レコード | checked_at降順で返す |

**Phase 2: 90%カバレッジ到達の安全網**

| テストケース | シナリオ | 期待結果 |
|------------|---------|---------|
| `test_delete_existing_returns_true` | 既存レコードを削除 | Trueを返し、以降のgetはNone |
| `test_delete_nonexistent_returns_false` | 存在しないレコードを削除 | Falseを返す |
| `test_list_all_returns_all_states` | 複数の状態を保存 | 全てのリストを返す |
| `test_concurrent_reads_succeed` | 同一DBへの並列読み取り | ロックエラーなく全読み取り成功 |

**主要エッジケース:**
- 並行アクセス（複数リーダー）、欠損レコード（None処理）
- 空の結果セット、オプションフィールドのNULL処理
- タイムスタンプのシリアライズ/デシリアライズ

#### 3.3 `detection/` モジュール

##### 3.3.1 コンポーネントインターフェース定義

各コンポーネントの想定インターフェース:

**URL Extractor:**
```python
@dataclass(frozen=True, slots=True)
class ExtractionConfig:
    selector: str
    attribute: str = "href"
    exclude_selectors: tuple[str, ...] = ()

def extract_urls(html: str, config: ExtractionConfig) -> list[str]: ...
```

**URL Normalizer:**
```python
@dataclass(frozen=True, slots=True)
class NormalizationConfig:
    strip_fragments: bool = True
    strip_tracking_params: bool = True
    force_https: bool = True
    normalize_trailing_slash: bool = True
    lowercase_host: bool = True

def normalize_url(url: str, base_url: str | None = None, config: NormalizationConfig | None = None) -> str: ...
def normalize_urls(urls: list[str], base_url: str, config: NormalizationConfig | None = None, deduplicate: bool = True) -> list[str]: ...
```

**URL Fingerprinter:**
```python
def fingerprint_urls(urls: list[str]) -> str: ...  # SHA-256 hex (64 chars)
def has_changed(old_fingerprint: str | None, new_fingerprint: str) -> bool: ...
```

**Feed Detector:**
```python
@dataclass(frozen=True, slots=True)
class FeedEntry:
    id: str
    title: str | None
    link: str | None
    published: datetime | None

@dataclass(frozen=True, slots=True)
class ParsedFeed:
    url: str
    title: str | None
    entries: tuple[FeedEntry, ...]

def detect_feed_urls(html: str, base_url: str) -> list[FeedInfo]: ...
def parse_feed(content: str, feed_url: str) -> ParsedFeed | None: ...
```

**HTTP Fetcher:**
```python
@dataclass(frozen=True, slots=True)
class FetchResult:
    status_code: int
    content: str | None
    etag: str | None
    last_modified: str | None
    is_modified: bool

class HttpFetcher:
    async def fetch(self, url: str, etag: str | None = None, last_modified: str | None = None) -> FetchResult: ...
```

##### 3.3.2 Property-Based Testing戦略

Hypothesisを使用したProperty-Based Testingの適用方針:

| コンポーネント | PBT適合度 | PBT割合 | Example割合 | 主なプロパティ |
|--------------|-----------|---------|-------------|---------------|
| URL Fingerprinter | ⭐⭐⭐ | 95% | 5% | 決定性、64文字hex、順序依存性 |
| URL Normalizer | ⭐⭐⭐ | 70% | 30% | 冪等性、小文字化、tracking param削除 |
| URL Extractor | ⭐⭐ | 30% | 70% | クラッシュ耐性、部分集合性 |
| Feed Detector | ⭐⭐ | 20% | 80% | クラッシュ耐性、ID非空 |
| HTTP Fetcher | ❌ | 0% | 80% unit + 20% integration | I/O依存のためPBT不適 |

**PBT適用基準:**
- **⭐⭐⭐ (PBT主体)**: 純粋関数で数学的不変条件が明確
- **⭐⭐ (PBT補助)**: Example-based中心、クラッシュ耐性テストにPBT
- **❌ (PBT不適)**: I/O依存、モックが必要

**依存追加:**
```toml
[dependency-groups]
dev = [
    "hypothesis>=6.100.0",
]
```

**ユニットテスト（35+シナリオ）:**

| コンポーネント | テストシナリオ |
|--------------|--------------|
| **URL Extractor** | 有効なHTMLとセレクタ、要素なしで空文字列、複数マッチで連結、無効なセレクタでエラー、exclude_selectorsでフィルタ |
| **URL Normalizer** | スキーム小文字化、https昇格、末尾スラッシュ正規化、utm_*パラメータ削除、フラグメント削除、相対URL解決、国際化ドメイン、空URL、不正URL、重複排除、順序保持 |
| **URL Fingerprinter** | SHA256 hex digest（64文字）、決定的ハッシュ（同一入力→同一ハッシュ）、異なる入力→異なるハッシュ、空リスト→決定的ハッシュ、順序が影響（異なる順序→異なるハッシュ） |
| **Feed Detector** | HTML `<link>` からRSS自動検出、Atom自動検出、共通パスへのフォールバック（`/feed`、`/rss.xml`）、無効なフィードはNone、フィードパースでエントリID抽出、エントリなしで空、不正XMLを適切に処理 |
| **Fetcher Retry** | タイムアウト後にリトライして成功、最大リトライ消費後に例外、4xxエラーでリトライなし、指数バックオフのタイミング、5xxでリトライ |

**統合テスト（5シナリオ）:**

| テストケース | シナリオ | 期待結果 |
|------------|---------|---------|
| `test_fetch_with_respx_mock_success` | HTTP 200でHTMLコンテンツ | パース済みレスポンスを返す |
| `test_fetch_handles_redirect` | HTTP 301 → 200 | リダイレクトを追跡し、最終コンテンツを返す |
| `test_fetch_respects_timeout` | モックサーバの遅延 > タイムアウト | ReadTimeoutを送出 |
| `test_conditional_get_with_etag` | ETagマッチで2回目のfetch | 304 Not Modifiedを返す |
| `test_feed_detection_integration` | 実HTML → フィード検出 → パース | エンドツーエンドのフィードURL抽出 |

**主要エッジケース:**
- タイムアウト（connect vs read）、不正フィード（不完全XML、欠損フィールド）
- URLエンコーディング（非ASCII文字、パーセントエンコード）
- 空レスポンス、無効なセレクタ、リダイレクトチェーン、特殊文字を含むフィードGUID

#### 3.4 `notifications/` モジュール

**ユニットテスト（5シナリオ）:**

| テストケース | シナリオ | 期待結果 |
|------------|---------|---------|
| `test_slack_notifier_sends_correct_payload` | ブログ更新で通知 | WebhookがフォーマットされたJSONを受信 |
| `test_slack_notifier_formats_message` | 複数ブログの変更 | メッセージに全blog IDとURLを含む |
| `test_slack_notifier_handles_webhook_failure` | Webhookが5xxを返す | リトライ処理用の例外を送出 |
| `test_slack_notifier_does_not_retry_on_4xx` | Webhookが400を返す | リトライなしで例外を送出 |
| `test_slack_notifier_timeout_raises_error` | Webhookリクエストがタイムアウト | タイムアウト例外を送出 |

**統合テスト:** なし（外部依存; ユニットレベルでモック）

**主要エッジケース:**
- Webhook失敗（ネットワークエラー、無効なレスポンス）
- ペイロードフォーマット（JSONシリアライズ、エスケープ）
- タイムアウト、レート制限（429レスポンス）

#### 3.5 `core/` モジュール

**ユニットテスト（8シナリオ）:**

| テストケース | シナリオ | 期待結果 |
|------------|---------|---------|
| `test_watcher_check_all_iterates_blogs` | 3つのブログを持つConfig | 各ブログでdetector.checkを呼び出す |
| `test_watcher_notifies_on_change_detected` | Detectorがchanged=Trueを返す | notifier.notifyを呼び出す |
| `test_watcher_skips_notification_if_unchanged` | Detectorがchanged=Falseを返す | notifierを呼び出さない |
| `test_watcher_continues_on_single_blog_error` | 1ブログが例外、他は成功 | 全ブログを処理しエラーをログ |
| `test_scheduler_registers_job_on_start` | Scheduler.start()を呼び出す | 正しいインターバルで定期ジョブを登録 |
| `test_scheduler_shutdown_stops_jobs` | Scheduler.shutdown()を呼び出す | 全ジョブ停止、保留タスクなし |
| `test_health_checker_returns_healthy` | 全コンポーネントが正常 | ステータスHEALTHYで全チェックTrue |
| `test_health_checker_returns_unhealthy` | DBチェック失敗 | ステータスUNHEALTHYでdatabase=False |

**統合テスト（4シナリオ）:**

| テストケース | シナリオ | 期待結果 |
|------------|---------|---------|
| `test_scheduler_executes_job_at_interval` | 1秒間隔でジョブをスケジュール | 2.5秒で2回以上実行 |
| `test_graceful_shutdown_completes_current_job` | ジョブ実行中にSIGTERM | シャットダウン前に現在のジョブ完了 |
| `test_watcher_end_to_end_with_real_db` | SQLiteで完全チェックサイクル | 状態が永続化され、履歴が記録される |
| `test_health_endpoint_responds_correctly` | HTTP GET /health | JSONステータスで200を返す |

**主要エッジケース:**
- グレースフルシャットダウン（シグナル処理）
- スケジューラタイミング（ジョブ間隔、重複ジョブ）
- 部分的失敗（一部ブログ失敗、他は成功）

---

### 4. TDDワークフロー規律

#### Red-Green-Refactor サイクル

```
┌─────────────────────────────────────────────────────────┐
│                    TDD CYCLE                            │
│                                                         │
│   ┌─────────┐    ┌─────────┐    ┌─────────────┐        │
│   │   RED   │───▶│  GREEN  │───▶│  REFACTOR   │───┐    │
│   │  Write  │    │  Write  │    │   Improve   │   │    │
│   │ failing │    │ minimal │    │    code     │   │    │
│   └─────────┘    └─────────┘    └─────────────┘   │    │
│        ▲                                          │    │
│        └──────────────────────────────────────────┘    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

#### 5つのTDD規律ルール

1. **失敗するテストなしに本番コードを書かない**
   - テストを先に書き、正しい理由で失敗することを確認
   - 失敗メッセージが欠落箇所を示すこと

2. **最小実装**
   - テストを通す最低限の実装を書く
   - 現在のテストで不要な機能は入れない

3. **Greenでリファクタ**
   - 全テストが通った状態でのみリファクタ
   - 各リファクタ後にテストを実行
   - メソッド抽出、変数名改善、重複排除

4. **テストファイル命名規約**
   ```
   src/blog_watcher/detection/url_extractor.py
   → tests/unit/detection/test_url_extractor.py

   src/blog_watcher/storage/repository.py
   → tests/integration/storage/test_repository.py
   ```

5. **テスト関数命名パターン**
   ```
   test_<method>_<scenario>_<expected_outcome>

   例: test_extract_with_valid_selector_returns_content
       test_extract_with_missing_element_returns_empty_string
   ```

#### モック vs 実装の判断ツリー

```
コンポーネントはI/Oを行うか?
├─ Yes
│  ├─ ネットワークI/O（HTTP、API呼び出し）?
│  │  └─ respxモックを使用（ユニットテスト）
│  ├─ データベースI/O（SQLite）?
│  │  └─ tmp_pathで実DBを使用（統合テスト）
│  └─ ファイルシステムI/O?
│     └─ tmp_pathで実ファイルを使用
└─ No
   └─ モック不要（純粋関数テスト）

例外: detector/watcherのユニットテストでビジネスロジックを
分離するため、リポジトリインターフェースにはプロトコルベースの
インメモリモックを使用する。
```

#### テストディレクトリ構成

```
tests/
├── conftest.py              # 共有フィクスチャ
├── factories.py             # factory-boyテストデータファクトリ
├── unit/
│   ├── conftest.py          # ユニット固有フィクスチャ（モックリポジトリ）
│   ├── config/
│   ├── detection/
│   └── notifications/
├── integration/
│   ├── conftest.py          # 統合固有フィクスチャ（実DB）
│   ├── storage/
│   ├── detection/
│   └── core/
└── e2e/
    ├── conftest.py          # E2E固有フィクスチャ（Docker）
    └── test_health.py
```

---

### 5. プロジェクト固有のテスト設計パターン

#### 5.1 respxによる非同期HTTPテスト

**パターン:** `respx.MockRouter` でHTTPリクエストをインターセプトし、実ネットワーク呼び出しを回避。

**原則:** テストは即座に実行; 待機や遅延なし。

```python
# タイムアウトを即座にシミュレート
respx_mock.get(url).mock(side_effect=httpx.ReadTimeout("timeout"))
```

#### 5.2 Tenacityリトライロジックのテスト

**パターン:** `side_effect` リストで一時的失敗をシミュレートし、`call_count` を検証。

```python
route = respx_mock.get(url).mock(side_effect=[
    httpx.ReadTimeout("timeout"),  # 1回目失敗
    httpx.Response(200, text="ok"),  # 2回目成功
])
assert route.call_count == 2
```

#### 5.3 URL正規化のテスト

**パターン:** `@pytest.mark.parametrize` で12+の多様なURLケースをカバー。

テストケース: スキーム正規化、末尾スラッシュ、utm_*削除、フラグメント削除、相対URL解決、国際化ドメイン、空文字列、冪等性

#### 5.4 フィード検出のテスト

**パターン:** 代表的なフィードフィクスチャ（RSS、Atom）でパースを検証。

```
tests/fixtures/feeds/
├── rss_valid.xml         # 標準RSS 2.0
├── atom_valid.xml        # 標準Atom 1.0
├── rss_no_guid.xml       # GUIDなし（linkを使用）
└── feed_malformed.xml    # 不完全なXML
```

#### 5.5 スケジューラのテスト

**パターン:** 短いインターバル（1秒）+ `asyncio.sleep()` を使用。

**原則:** `@pytest.mark.slow` で遅いテストをマークし、オプションで除外可能に。

---

### 6. モック戦略

#### レイヤ別モックアプローチ

| コンポーネント | モック戦略 | ツール | 理由 |
|--------------|-----------|--------|-----|
| `httpx.AsyncClient` | リクエストインターセプト | `respx` | パターンマッチと応答シミュレーション |
| `SQLite` | 実DB（tmp） | `tmp_path` フィクスチャ | SQLの正当性には実行が必要 |
| `Slack Webhook` | リクエストインターセプト | `respx` | ペイロード形式検証、外部呼び出し回避 |
| `APScheduler` | プロトコルモック | `unittest.mock` | ジョブ登録のみ検証 |
| `datetime.now()` | 時刻固定 | `freezegun` | 決定的タイムスタンプ |
| `structlog` | ログ捕捉 | `structlog.testing` | I/Oなしでログ検証 |

#### プロトコルベースモック

ADR-006のプロトコルベースインターフェースにより、依存の差し替えが容易。ユニットテストでは `MockBlogStateRepository`（インメモリ実装）を使用し、`unittest.Mock` より型安全かつ状態保持可能。

---

### 7. CI統合

#### GitHub Actions ワークフロー

設定は `.github/workflows/test.yml` に定義。主要ステップ:

1. `uv sync --dev` で依存関係インストール
2. `uv run ruff check src tests` でリント
3. `uv run mypy src` で型チェック
4. `uv run pytest --cov=src/blog_watcher --cov-fail-under=85` でテスト実行
5. Codecovへカバレッジアップロード

#### pytest設定

`pyproject.toml` の `[tool.pytest.ini_options]` を参照。主要設定:

- `testpaths = ["tests"]`
- `asyncio_mode = "auto"`
- マーカー: `unit`, `integration`, `e2e`, `slow`

#### テスト実行コマンド

```bash
# TDD中の高速フィードバック
uv run pytest -m unit -x --ff

# プリコミット（E2Eスキップ）
uv run pytest -m "not e2e"

# CI（フルスイート）
uv run pytest --cov=src/blog_watcher --cov-fail-under=85
```

---

### 8. 実装フェーズ

現状は最小限のテスト基盤（`tests/__init__.py`のみ）。段階的に実装する:

**Phase 1:** pyproject.tomlにテスト依存を追加し、コアフィクスチャ付きconftest.py作成

**Phase 2:** `config/` のユニットテスト（最高カバレッジ対象）

**Phase 3:** `detection/` のユニットテスト（コアロジック）

**Phase 4:** `storage/` リポジトリの統合テスト

**Phase 5:** CIワークフローとカバレッジ報告の設定

**Phase 6:** CLI起動ベースのE2Eスモークを追加（Slack APIで送信確認）

---

## 結果

### ポジティブ

- **高い信頼性**: 85%カバレッジと意味のあるテストがリグレッションを早期検出
- **速いフィードバック**: ユニットテストが <10s で実行されTDDが回しやすい
- **保守性**: プロトコルベースのモックとFactoryでテストが壊れにくい
- **CIの安定性**: 時間固定でフレークを防止
- **ドキュメント性**: テストが実行可能な仕様になる

### ネガティブ

- **セットアップコスト**: factory-boy/respx/freezegunの学習コスト
- **テスト保守**: テストコード自体が増える
- **遅いE2E**: Docker E2EでCIに約60秒追加

### リスク

- **過剰モック**: テストは通るが本番で失敗するリスク
  - 対策: 実SQLite統合テスト; E2Eスモーク
- **テスト汚染**: テスト間の共有状態で断続的に失敗
  - 対策: pytest-randomlyで順序依存を検出; functionスコープフィクスチャ

---

## 検証チェックリスト

### ADRとの整合性確認

| ADR-002 シナリオ | テストケース |
|-----------------|-------------|
| RSS/Atom検出 | `detection/test_feed_detector.py`（7シナリオ） |
| sitemap.xmlパース | `detection/test_sitemap_detector.py`（5シナリオ） |
| HTML URL抽出 | `detection/test_url_extractor.py`（5シナリオ） |
| URL正規化 | `detection/test_url_normalizer.py`（12+シナリオ） |
| 条件付きGET | `integration/detection/test_fetcher.py`（ETag/Last-Modified） |

| ADR-005 エラーカテゴリ | テストケース |
|---------------------|-------------|
| 一時的エラー | `test_fetcher_retry.py`（タイムアウト、5xxでリトライ） |
| 永続的エラー | `test_watcher.py`（404処理、consecutive_errorsインクリメント） |
| レート制限 | `test_fetcher_retry.py`（429とRetry-Afterヘッダー） |
| 設定エラー | `config/test_loader.py`（検証失敗） |

| ADR-006 モジュール | ユニットテスト | 統合テスト |
|------------------|--------------|-----------|
| `config/` | 5 | 0 |
| `storage/` | 0 | 8 |
| `detection/` | 35+ | 5 |
| `notifications/` | 5 | 0 |
| `core/` | 8 | 4 |
| **合計** | **53+** | **17** |
