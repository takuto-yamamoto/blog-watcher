# ADR-003: Storage Solution

## Status

Accepted

## Decision

### Database: SQLite

**Why:** ゼロ構成でアプリケーションに組み込み可能。単一ファイルでバックアップ・移行が容易。単一インスタンスデプロイメントに最適。Python標準ライブラリ（sqlite3）で追加依存なし。

**Not Chosen:**
- `PostgreSQL` - 外部プロセス・接続管理が必要、単一インスタンスアプリには過剰
- `JSON/TOMLファイル` - 並行アクセス時のデータ整合性が保証できない、クエリ機能なし
- `Redis` - 永続化設定が必要、メモリ消費が大きい、外部依存

### Schema Design

```sql
-- ブログの現在の状態（HTTPヘッダー・URL指紋・feed/sitemapの有無）
CREATE TABLE blog_state (
    blog_id       TEXT PRIMARY KEY,  -- TOMLのblog識別子
    etag          TEXT,              -- Last ETag header value
    last_modified TEXT,              -- Last Last-Modified header value
    url_fingerprint TEXT,            -- Hash of normalized URL list
    feed_url      TEXT,              -- NULL if not detected
    sitemap_url   TEXT,              -- NULL if not detected
    recent_entry_keys TEXT,           -- JSON array for last N feed entry keys
    last_check_at TEXT NOT NULL,     -- ISO8601 timestamp
    last_change_at TEXT              -- ISO8601 timestamp (NULL if never changed)
);

-- チェック履歴（デバッグ・統計用）
CREATE TABLE check_history (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    blog_id       TEXT NOT NULL,
    checked_at    TEXT NOT NULL,     -- ISO8601 timestamp
    http_status   INTEGER,           -- HTTP response status code
    skipped       INTEGER NOT NULL DEFAULT 0,  -- 1 if skipped by ETag/Last-Modified
    changed       INTEGER NOT NULL DEFAULT 0,  -- 1 if new entry detected
    url_fingerprint TEXT,            -- URL fingerprint at this check (NULL if skipped)
    error_message TEXT               -- Error details if failed
);
```

### Index Strategy

```sql
-- 履歴検索用（blog_idでの絞り込み + 時系列ソート）
CREATE INDEX idx_check_history_blog_time ON check_history(blog_id, checked_at DESC);

-- 変更検出履歴の抽出用
CREATE INDEX idx_check_history_changed ON check_history(changed) WHERE changed = 1;
```

## Design Notes

### blogsテーブルを作らない理由

ブログ設定はTOML（`config.toml`）で管理し、DBには状態のみを保存する。

**Why:** Single Source of Truth。設定変更時にTOMLとDBの同期問題を回避。TOMLはGit管理可能でレビュー・ロールバックが容易。

### blog_stateの設計方針

- `etag`/`last_modified`: HEAD requestでの変更判定に使用。サーバーが返さない場合はNULL。
- `url_fingerprint`: sitemap/HTMLで得たURL一覧を正規化してハッシュ化し、差分判定に使う。
- `feed_url`/`sitemap_url`: 未検出の場合はNULL。一定間隔で再探索するための状態。
- `recent_entry_keys`: feedの先頭N件のキーをJSON配列で保存し、新規判定に使用。
- タイムスタンプはISO8601文字列で保存（SQLiteにはDATETIME型がないため、文字列比較で正しくソート可能）。

### check_historyの保持期間

履歴は無制限に蓄積される設計。必要に応じてcronや起動時に古いレコードを削除する運用を想定。

```sql
-- 例: 30日以上前の履歴を削除
DELETE FROM check_history
WHERE checked_at < datetime('now', '-30 days');
```
