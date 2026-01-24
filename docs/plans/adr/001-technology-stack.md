# ADR-001: Technology Stack

## Status

Accepted

## Decision

### Package Manager: `uv`

**Why:** Rust製で依存解決・インストールが高速（pip比10-100倍）。`uv.lock`による再現可能なビルド。venv作成から依存管理まで単一ツールで完結。

**Not Chosen:**
- `poetry` - 依存解決が遅い、独自のlock形式
- `pip` + `pip-tools` - 複数ツールの組み合わせが必要、lockfile管理が煩雑

### Build Backend: `hatchling`

**Why:** PEP 517準拠でモダン。pyproject.tomlのみで設定完結。uvとの相性が良い。

**Not Chosen:**
- `setuptools` - setup.py/setup.cfgが必要になりがち、設定が冗長

### HTTP Client: `httpx`

**Why:** 同じAPIでsync/async両対応。HTTP/2ネイティブサポート。コネクションプーリング内蔵。

**Not Chosen:**
- `requests` - syncのみ、HTTP/2非対応
- `aiohttp` - asyncのみ、sync利用時にAPI が異なる

### HTML Parser: `lxml`

**Why:** C実装で高速。壊れたHTMLも適切に処理。BeautifulSoupのバックエンドとして最適。

**Not Chosen:**
- `html.parser` (stdlib) - 遅い、malformed HTMLの処理が弱い
- `html5lib` - 最も正確だが非常に遅い

### Scheduler: `APScheduler`

**Why:** ジョブの永続化サポート（SQLite jobstore）。プロセス内で動作し外部依存なし。

**Not Chosen:**
- `celery` - Redis/RabbitMQ等のbrokerが必要、単一プロセスアプリには過剰
- `cron` (system) - コンテナ化が複雑、外部依存

### Logging: `structlog`

**Why:** JSON出力でコンテナログ集約に最適。コンテキストバインディングでrequest_id等を自動付与。

**Not Chosen:**
- `loguru` - シンプルだが構造化出力の制御が弱い

### CLI: `typer`

**Why:** 型ヒントがそのままCLI引数になる。`--help`自動生成。click基盤で信頼性あり。

**Not Chosen:**
- `click` - 機能は同等だがボイラープレートが多い
- `argparse` (stdlib) - 手動でヘルプ記述、型変換が必要

## Other Choices

以下は有力な代替案がないため選定理由を省略:
- Python 3.12, beautifulsoup4, pydantic, pyyaml, SQLite
