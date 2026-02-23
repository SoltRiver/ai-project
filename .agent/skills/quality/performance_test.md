---
name: Performance_Test
description: 品質管理エージェント用パフォーマンス測定・チューニングスキル。エンドポイント応答速度・DBクエリ効率・テンプレート描画・静的資産を体系的に計測し、改善指針を提示する。
---

# Performance Test & Tuning Skill

品質管理エージェントとして、アプリケーション全体のパフォーマンスを体系的に
**測定**し、問題があれば具体的な**チューニング方針**を提示するスキルです。

## 前提条件
- Uvicorn サーバーが起動していること（`http://127.0.0.1:8000`）
- Python 環境で `requests` パッケージが使用可能であること
- `scripts/perf_check.py` が利用可能であること

## 技術前提
- **Stack**: FastAPI + Jinja2 + htmx（SPA不可 / Vanilla JS 最小限）
- **DB**: SQLite（SQLAlchemy ORM）
- **外部API**: yfinance, EDINET API, J-Quants API

---

## 1. エンドポイント応答速度テスト

### 閾値定義
| カテゴリ | 目標(ms) | 警告(ms) | NG(ms) |
|---|---|---|---|
| 静的ページ（Glossary, Candle等） | < 100 | 100–500 | > 500 |
| DB参照ページ（Home, Calendar等） | < 500 | 500–2000 | > 2000 |
| 外部API依存（Indices, News等） | < 3000 | 3000–5000 | > 5000 |
| htmx パーシャル | < 300 | 300–1000 | > 1000 |
| JSON API | < 200 | 200–500 | > 500 |

### チェック項目
| # | 観点 | 確認内容 | 判定基準 |
|---|---|---|---|
| P-1 | 初回応答 | 各エンドポイントの初回レスポンスタイム | カテゴリ別閾値以内 |
| P-2 | 安定性 | 3回計測の標準偏差 | 平均の50%以内 |
| P-3 | ウォームアップ | 2回目以降の改善有無 | 初回比で改善傾向 |
| P-4 | htmx タブ切替 | タブパーシャルの応答速度 | < 300ms |
| P-5 | 検索API | オートコンプリートの応答速度 | < 200ms |

### 対象エンドポイント
```
# 静的ページ
GET /glossary
GET /candle-patterns

# DB参照ページ
GET /                      （銘柄一覧）
GET /calendar

# 外部API依存
GET /indices
GET /news

# htmx パーシャル
GET /stocks/{code}/tab/{tab}
GET /partials/edinet/diff_summary?doc_id=...
GET /partials/calendar/day?date=...
GET /partials/calendar/month_grid?year=...&month=...

# JSON API
GET /api/stocks/search?q=...
GET /edinet/health
GET /edinet/documents?date=...
GET /fundamentals/edinet/{doc_id}
```

### 実行方法
```bash
# 自動計測スクリプトを使用
$env:PYTHONIOENCODING='utf-8'; python scripts/perf_check.py

# 手動での個別計測
python -c "
import requests, time
s = time.perf_counter()
r = requests.get('http://127.0.0.1:8000/TARGET', timeout=30)
ms = (time.perf_counter()-s)*1000
print(f'{r.status_code} {ms:.0f}ms')
"
```

---

## 2. DB クエリ効率テスト

### チェック項目
| # | 観点 | 確認内容 | 判定基準 |
|---|---|---|---|
| Q-1 | N+1 問題 | 一覧表示で N+1 クエリが発生していないか | ログで INSERT/SELECT 件数確認 |
| Q-2 | インデックス | WHERE/ORDER BY 対象カラムにインデックスがあるか | EXPLAIN で確認 |
| Q-3 | 不要カラム取得 | SELECT * の使用有無 | 必要カラムのみ取得 |
| Q-4 | キャッシュ活用 | 頻繁アクセスデータがキャッシュされているか | 同一リクエスト2回で速度差 |

### 確認方法
```python
# SQLAlchemy のクエリログ有効化
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# EXPLAIN による実行計画確認
# sqlite> EXPLAIN QUERY PLAN SELECT ...;
```

### チューニング指針
1. **N+1 検出** → `joinedload()` / `selectinload()` に変更
2. **インデックス不足** → `Index()` を追加（マイグレーション注意）
3. **SELECT *** → 必要カラムのみに限定
4. **キャッシュ** → `functools.lru_cache` / メモリ辞書キャッシュ検討

---

## 3. テンプレート描画効率テスト

### チェック項目
| # | 観点 | 確認内容 | 判定基準 |
|---|---|---|---|
| T-1 | テンプレート分割 | 大きなHTMLが適切にパーシャル化されているか | 1ファイル < 300行 |
| T-2 | ループ内計算 | Jinja2 の for ループ内で重い処理がないか | フィルター/マクロに切り出し |
| T-3 | 条件分岐 | 不要なブロックが毎回評価されていないか | htmx で遅延読み込み化 |
| T-4 | htmx 最適化 | 全体リロードではなくパーシャル更新を使用 | hx-target で差分更新 |

### チューニング指針
1. **巨大テンプレート** → `{% include %}` でパーシャル分割
2. **ループ内計算** → サービス層で事前計算、テンプレートは表示のみ
3. **遅延読み込み** → `hx-trigger="revealed"` で画面外コンテンツを遅延
4. **キャッシュ** → Jinja2 の `{% cache %}` 拡張、または静的部分の事前レンダリング

---

## 4. 静的資産最適化テスト

### チェック項目
| # | 観点 | 確認内容 | 判定基準 |
|---|---|---|---|
| S-1 | CSS サイズ | theme.css のファイルサイズ | < 100KB（実用目安） |
| S-2 | JS サイズ | app.js のファイルサイズ | < 100KB |
| S-3 | 画像サイズ | 単一画像のファイルサイズ | < 500KB |
| S-4 | キャッシュバスティング | CSS/JS に ?v= パラメータがあるか | 更新時にバージョン更新 |
| S-5 | 未使用CSS | 使われていないCSSルールがないか | スタイル肥大化防止 |

### 計測方法
```bash
# ファイルサイズ確認
Get-ChildItem static/css/*.css, static/js/*.js | Select Name, Length
Get-ChildItem static/images/* | Where { $_.Length -gt 500KB } | Select Name, Length
```

### チューニング指針
1. **CSS 肥大化** → 未使用ルール削除、コンポーネント別分割
2. **画像最適化** → WebP 変換 / 適切なサイズにリサイズ
3. **JS 最小化** → 不要な処理の削除（ビルドツール不使用のため手動）
4. **gzip 配信** → FastAPI middleware で静的資産を圧縮配信

---

## 5. 外部API呼び出し最適化テスト

### チェック項目
| # | 観点 | 確認内容 | 判定基準 |
|---|---|---|---|
| E-1 | 直列呼び出し | 複数API呼び出しが直列になっていないか | asyncio.gather 等で並列化 |
| E-2 | タイムアウト | 外部API呼び出しにタイムアウトが設定されているか | requests.get(timeout=N) |
| E-3 | キャッシュ | 同一データの重複取得がないか | TTL付きキャッシュ利用 |
| E-4 | フォールバック | API失敗時にキャッシュデータで応答可能か | graceful degradation |
| E-5 | レート制限 | API呼び出し頻度が制限内か | 429エラーが出ていない |

### チューニング指針
1. **直列→並列** → `asyncio.gather()` / `concurrent.futures`
2. **キャッシュ導入** → `functools.lru_cache` + TTL / DB キャッシュ
3. **タイムアウト** → 全HTTP呼び出しに `timeout=10` 以下を設定
4. **バックグラウンド更新** → `BackgroundTasks` で非同期キャッシュ更新

---

## 実行フロー（推奨手順）

### Phase 1: 全体計測（自動）
1. `scripts/perf_check.py` を実行し、全エンドポイントの応答速度を取得
2. 閾値を超えるエンドポイントを特定

### Phase 2: ボトルネック分析
1. 閾値超過エンドポイントの処理内訳を調査
   - DB クエリ？ → Phase 2a: SQLAlchemy ログ確認
   - 外部API？ → Phase 2b: API応答時間の個別計測
   - テンプレート？ → Phase 2c: テンプレート行数/複雑度確認
2. 原因を特定して記録

### Phase 3: 静的資産チェック
1. CSS / JS / 画像のサイズ確認
2. キャッシュバスティングの設定確認

### Phase 4: チューニング提案
1. 検出された問題ごとに改善案を提示（優先度付き）
2. 改善前後の比較が可能なベンチマーク手順を明記

### Phase 5: チューニング実施後の再計測
1. 修正後に `scripts/perf_check.py` を再実行
2. 改善率を計算して報告

---

## 出力フォーマット

### パフォーマンスサマリー
| エンドポイント | カテゴリ | 平均(ms) | 閾値(ms) | 判定 |
|---|---|---|---|---|
| `/` | DB参照 | 1,597 | < 2,000 | ✅ PASS |
| `/indices` | 外部API | 1,528 | < 3,000 | ✅ PASS |
| `/glossary` | 静的 | 16 | < 100 | ✅ PASS |

### ボトルネック分析（NG/WARNING のみ）
| エンドポイント | 原因 | 詳細 | 優先度 |
|---|---|---|---|
| `/news` | 外部API | yfinance 直列呼び出し | HIGH |

### チューニング提案
| # | 対象 | 現状 | 提案 | 期待改善 | 難易度 |
|---|---|---|---|---|---|
| 1 | `/news` | 直列API呼び出し | asyncio.gather | -50% | 中 |

### 静的資産
| ファイル | サイズ | 判定 |
|---|---|---|
| theme.css | 85KB | ✅ |
| app.js | 42KB | ✅ |

---

## チェックリスト

- [ ] Phase 1: 全体計測完了
- [ ] Phase 2: ボトルネック分析完了
- [ ] Phase 3: 静的資産チェック完了
- [ ] Phase 4: チューニング提案作成（必要な場合）
- [ ] Phase 5: チューニング実施後の再計測（実施した場合）
- [ ] 結果レポートを出力

## 参照スキル
- `ops/perf_tuner.md` — 個別ボトルネック解消の詳細手順
- `quality/ui_test.md` — UI観点のパフォーマンスチェック（P-1〜P-4）
