# ADR-002: Change Detection Strategy

## Status

Accepted

## Decision

シングルプロセスでシンプルに動作させる前提で、以下の順で変更検知を行う。

**スキップルール:** 新規エントリを検知した時点で終了する。新規なしの場合は次段へ進む。

### 1. RSS/Atom

1. HTML内の`<link rel="alternate">`検索
   1. `type="application/rss+xml"`
   2. `type="application/atom+xml"`
   3. `type*="xml"`
   4. href が `rss|atom|feed|xml` を含む
2. 定番URLパス検索
   1. `/feed /rss /atom /feed.xml /rss.xml /atom.xml /index.xml /feed/ /rss/ /atom/`
3. feedっぽいURLを`feedparser`に入れてfeedかどうかチェック
   1. `entries` が存在し、`bozo` などのエラーが致命的でないことを確認
4. feedの先頭N件のキーの中に未見があれば新着
   1. キーは `guid` > `link` > `title+published` の順で採用
   2. 直近N件を保存し、未見があれば新着
5. feed URLをDB保存（未検出の場合は一定間隔で再探索）

### 2. sitemap.xml

1. URLパターン(configurable)に応じてURL一覧化
2. 正規化
3. 差分比較
4. sitemap有無をDB保存（未検出の場合は一定間隔で再探索）

### 3. HTML内のURL正規化して差分検知

1. URLパターン(configurable)に応じてURL一覧化
2. 正規化
3. 差分比較

### 4. HTTP取得ポリシー

GETで取得し、`ETag`/`Last-Modified`が取得できた場合は次回以降のGETで
`If-None-Match`/`If-Modified-Since`を使って条件付きGETにする。

**Why:** HEAD非対応や誤実装を避けつつ、変更なしの場合は軽量なレスポンスで済む。

### 5. URLパターンと正規化

- デフォルトはzero-config（汎用的な記事URLパターンを内蔵）
- ただしconfigurableにし、ユーザーが上書き可能とする
- URL正規化は以下を行う
  - scheme/hostを小文字化
  - `http`/`https` を統一（可能なら `https`）
  - 末尾スラッシュの統一
  - クエリはトラッキング系（`utm_*` 等）を削除
  - フラグメント（`#...`）は削除

**Not Chosen:**
- 全HTML比較 - 動的要素で常に変更検出、誤検知多発
- LLMを使った要約/差分判定 - 実行コストと不安定性が高い
- 画像解析による差分判定 - 高コストで誤検知が多い
- レンダリング（ヘッドレスブラウザ）前提の判定 - 実行コストと運用負荷が高い
