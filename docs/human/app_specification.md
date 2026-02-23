# 株価分析アプリ（StockAnalyst AI）仕様書

> **最終更新日**: 2026-02-23
> **バージョン**: v2.2

## 1. 概要

本アプリケーションは、初心者から中級者の投資家を対象とした、**AIによる情報の要約と視覚的なデータ分析**を提供する株価分析ツールです。
リアルタイムの市場データ、ニュース、財務指標（ファンダメンタルズ）、およびテクニカル分析（キャンドルパターン）を統合し、投資判断のサポートを行います。

### 1.1 アプリ名称
- **ブランド名**: StockAnalyst AI
- **ヘッダー表示**: 📈 StockAnalyst **AI**

### 1.2 ナビゲーション構成
ヘッダーに以下のリンクを配置：

| 順序 | ラベル | パス | 概要 |
| :--- | :--- | :--- | :--- |
| 1 | 主要指標 | `/indices` | 国内外の主要市場指数一覧 |
| 2 | ニュース | `/news` | AI分析付きマーケットニュース |
| 3 | 株価リスト | `/stocks` | ウォッチリスト（ホーム） |
| 4 | ランキング | `/ranking` | 騰落率ランキング + AI解説 |
| 5 | 用語集 | `/glossary` | 投資用語のビジュアル解説 |
| 6 | ローソク足 | `/candle-patterns` | ローソク足パターン学習 |

- ルートパス `/` は `/stocks` へリダイレクト
- 右端にテーマ切替ボタン（ライト/ダーク）

---

## 2. 主要機能

### 2.1 銘柄管理（Stock List）
**パス**: `/stocks`

- **銘柄検索・追加**: 銘柄名またはコードによる検索。**J-Quants API V2** から上場銘柄マスターを取得し、前方一致検索とオートコンプリートを提供。ウォッチリストへの追加が可能。
  - オートコンプリート表示形式: `銘柄名（銘柄コード）`
  - 検索API: `/api/stocks/search?q=...`
- **銘柄削除**: チェックボックスで選択した銘柄を一括削除。
- **リスト表示**: 登録銘柄の現在値、前日比、騰落率を一覧で確認。
- **初期銘柄**: アプリ起動時にウォッチリストが空であれば、以下の5銘柄を自動登録:
  - トヨタ自動車(7203)、ソニーグループ(6758)、ソフトバンクグループ(9984)、三菱UFJ(8306)、東京エレクトロン(8035)
- **銘柄マスター同期**: アプリ起動時にバックグラウンドスレッドで `StockMasterService` を実行。J-Quants APIから上場銘柄マスターを1日1回同期（Free プラン対応のフォールバック戦略あり）。データがない場合はシードファイル (`data/seed_stock_master.json`) から投入。

### 2.2 銘柄詳細（Stock Detail）
**パス**: `/stocks/{code}`

タブ切り替え（htmx による部分更新）で以下の5つのビューを提供：

| タブ名 | アイコン | パス | 内容 |
| :--- | :--- | :--- | :--- |
| テクニカル分析 | 📈 | `/stocks/{code}/tab/chart` | チャート・テクニカル指標 |
| ファンダメンタル分析 | 📊 | `/stocks/{code}/tab/fundamental` | 財務データ・投資指標 |
| 配当 | 💰 | `/stocks/{code}/tab/dividend` | 配当履歴・配当利回り |
| 需給 | ⚖️ | `/stocks/{code}/tab/margin` | 信用残データ・需給分析 |
| 株主優待 | 🎁 | `/stocks/{code}/tab/shareholder` | 株主優待情報 |

#### 2.2.1 テクニカル分析タブ（Chart）
- **チャート描画**: Custom Canvas Implementation によるインタラクティブな株価チャート。
- **対応インターバル**: 1分足、5分足、10分足、日足、週足、月足。
- **テクニカル指標**:
  - 移動平均線（SMA）: 短期(25)、長期(75)。
  - トレンドライン（線形回帰）。
  - RSI（相対力指数）。
  - ゴールデンクロス / デッドクロスの自動検出・表示。
- **出来高分析**: 出来高バーをゴールド（#FFD700）で統一し、ツールチップで具体的な出来高（万株単位）を確認可能。
- **キャンドルパターン認識**: 全53種類のローソク足パターン（大陽線、包み足、はらみ足等）を自動検知。パターン名クリックでモーダルを表示。
  - モーダルはBullish/Bearishの両バリアント対応。
- **分析・シグナル情報**: サポートライン、トレンド判定、売買シグナル、リスク評価、ポジティブ要因を自動算出。

#### 2.2.2 ファンダメンタル分析タブ（Fundamental）
- **財務データ視覚化**: 売上高、営業利益、純利益、総資産、純資産の推移に加え、資産構成（純資産・負債）を円グラフで表示（Plotly.js）。
- **投資指標算出**: J-Quants API（株価データ）とEDINET（財務データ）を統合し、PER（株価収益率）、PBR（株価純資産倍率）、ROE（自己資本利益率）、EPS、BPSを自動算出・表示。
- **データソース（Hybrid）**: EDINET API v2（XBRL）+ J-Quants API（Daily Quotes / Listed Info）。
- **フォールバック機能**: 市場データ取得失敗時（または未認証時）でも、財務データのみを用いた分析レポートを表示可能。
- **EDINET 差分比較**: 前回の有価証券報告書との数値を自動比較し、「固定6指標」の増減と「変化の大きい項目（最大3件）」を表示。htmx 連携による非同期ロード（`/partials/edinet/diff_summary`）。

#### 2.2.3 配当タブ（Dividend）
- **配当データ取得**: J-Quants API を優先し、取得不可時は yfinance にフォールバック。
- **表示項目**: 配当履歴、配当利回り、配当性向（EPS ベース）、現在株価。
- **データソース表記**: "jquants" / "yfinance" / "none" のソース情報を表示。

#### 2.2.4 需給タブ（Supply/Demand）
- **データソース**: J-Quants API V2 `/markets/margin-interest` エンドポイントから信用取引週末残高を取得。
- **表示項目**（固定順）:
  1. **需給サイズ（相対）** — 総残高 / ADV20 を日数換算し「低・中・高」に分類。データ不足時は「暫定」表示。
  2. **構成比バー** — 買い残・売り残の100%横分割バー（バー外に%表示）。
  3. **絶対量** — 信用買い残・信用売り残・総残高（株数）。
  4. **前週比** — 増減株数 + 増減率%。
  5. **偏り分類** — 5段階（買い偏り強/弱、偏りなし、売り偏り弱/強）+ 判定保留。
  6. **信頼度** — ◎高 / 〇中 / △低 / —未確定。
  7. **注意文** — 「信用残は需給の一側面であり、価格の方向性を示すものではありません」
- **安全性設計**: 価格予測を想起させる文言は一切使用しない。色は淡色（muted）を使用。
- **ロジック**: `services/margin_service.py` に集約（ADV20算出時の外れ値クリップ、偏り5段階分類等）。
- **フォールバック**: API取得失敗時は「信用残データを取得できませんでした」メッセージを表示。

#### 2.2.5 株主優待タブ（Shareholder Benefits）
- 株主優待情報の表示（将来拡張向けの基盤実装済み）。

### 2.3 市場インデックス（Market Indices）
**パス**: `/indices`

- 以下の主要指数をYahoo Finance から個別取得し、現在値・前日比・騰落率を表示：

| 指標名 | ティッカー | 備考 |
| :--- | :--- | :--- |
| 日経平均 | ^N225 | |
| TOPIX | ^TOPX | 代替ティッカー |
| 日経平均先物 | NIY=F | |
| JASDAQ平均 | ^DJJAS | 代替ティッカー |
| NYダウ | ^DJI | |
| NASDAQ | ^IXIC | |
| マザーズ総合 | ^MOTHERS | 代替ティッカー |

- 各指標は個別に取得し、一部取得失敗でも他は表示可能（部分フォールバック設計）。

### 2.4 AIニュース（AI Market News）
**パス**: `/news`

- **ニュース収集**: Yahoo Finance 経由で以下のティッカーからニュースを並列取得（ThreadPool使用）:
  - 日経平均（^N225）、NYダウ（^DJI）、ドル円（JPY=X）
  - 各ティッカー最大5件、重複排除後、日付順で上位8件に絞り込み。
- **AI和訳・要約**: Gemini API（優先）で英語ニュースの翻訳・3行要約を自動生成。
- **市場影響分析**: ニュースが個別銘柄やセクターに与える影響（Positive/Negative）をAIが判定。
- **原文確認**: 翻訳前のタイトルをツールチップ等で確認可能。
- **フォールバック**: Gemini 失敗時は OpenAI（GPT-4o mini）に自動切り替え。

### 2.5 ランキング（Ranking）
**パス**: `/ranking`

- **騰落率ランキング**: 主要約100銘柄を対象に、日次・週次・月次・年次の値上がり/値下がりランキングを表示。
- **切り替え**: htmx による部分更新（`/ranking/list?type=top|bottom&period=today|week|month|year`）。
- **AI市場解説**: ランキング上位銘柄の動きの背景や今後の展望をGemini APIが分析してコメント。
  - AI分析失敗時はOpenAIにフォールバック。
- **日本語表示**: セクター名を自動翻訳（SECTOR_MAP定義）。

### 2.6 用語集（Glossary）
**パス**: `/glossary`

- **ビジュアル解説**: 投資用語をカード形式で一覧表示。各用語に直感的なイメージ画像を配し、初心者でも理解しやすい構成。
- **データソース**: `data/terms_data.py` に定義された用語リスト。

### 2.7 テクニカル分析・ローソク足パターン（Candle Patterns）
**パス**: `/candle-patterns`

- **パターン分類**: 全53種類のキャンドルパターン。
  - **Basic**（基本）: 18パターン — 大陽線、大陰線、包み足、はらみ足 等。
  - **Advanced**（応用）: 35パターン — 三尊天井、ダブルトップ/ボトム、フラッグ 等。
- **タブ切り替え**: htmx によるBasic/Advanced切り替え。
- **チャートパターン視覚化**: Plotly.js によって各パターンの模式チャートを動的生成（`utils/chart_pattern_visualizer.py` で20種以上のパターンチャートを実装）。
- **学習ガイド**: 各パターンの詳細な意味・推奨アクション・投資戦略をカード形式で解説。
- **チャート連携**: チャート上のパターンクリック → モーダルでパターン詳細を即座に確認。

### 2.8 EDINET書類検索（Document Search）
**パス**: `/api/edinet/documents/ui/search`

- **書類検索**: 日付指定（YYYY-MM-DD）および証券コードによる有価証券報告書の検索機能。
- **対象書類**: 有価証券報告書（docTypeCode: 120）。
- **分析連携**: 検索結果から直接ファンダメンタルズ分析レポート（2.9）へ遷移可能。

### 2.9 EDINET ファンダメンタルズ分析（Fundamental Analysis）
**パス**: `/api/fundamentals/reports/{doc_id}` （HTML）、`/api/fundamentals/edinet/{doc_id}` （JSON API）

- **XBRLパース**: EDINET書類のZIPダウンロード → XBRL解析 → 財務数値抽出。
  - EdinetClient → EdinetDocumentStore → EdinetXbrlLocator → EdinetFinancialExtractor のパイプライン。
- **市場データ連携**: J-Quants API から株価データを取得し、PER/PBR/ROE 等の投資指標を自動算出（`with_market=True` オプション）。
- **フォールバック**: J-Quants取得失敗時でも財務データのみのレポートを表示。

- `FinancialAnalyzer` サービスを使用したシンボルベースのファンダメンタル分析。
- EDINET 書類の検索・ダウンロード・解析を自動で実行。

### 2.11 EDINET 差分比較（Diff Feature）
**パス**: `/partials/edinet/diff_summary?doc_id=...`

- **自動比較**: 同一企業の「今回」と「前回」の有価証券報告書を自動特定し、財務数値を正規化した上で比較。
- **重要変化抽出**: 独自の「二段階閾値 + スケール・絶対額スコアリング」により、多数の勘定科目の中から投資家が注目すべき変化（売上高の急増、負債の減少等）を最大3件抽出。
- **固定指標表示**: 売上高、営業利益、親会社株主利益、総資産、純資産、自己資本比率の6項目を固定で比較表示。
- **免責事項**: 投資判断は自己責任である旨を明記。

---

## 3. 技術スタック

本アプリは、シンプルかつ高性能なサーバーサイドレンダリング（SSR）構成を採用しています。

### 3.1 バックエンド
| 項目 | 技術 | 備考 |
| :--- | :--- | :--- |
| 言語 | Python 3.11+ | |
| フレームワーク | FastAPI | 非同期対応、自動ドキュメント生成 |
| Webサーバー | Uvicorn | ASGI サーバー |
| テンプレートエンジン | Jinja2 | サーバーサイドレンダリング |
| ORM | SQLAlchemy 2.0+ | declarative_base 使用 |
| DB | SQLite（デフォルト） | PostgreSQL 対応可能（DATABASE_URL 環境変数で切替） |

### 3.2 フロントエンド
| 項目 | 技術 | 備考 |
| :--- | :--- | :--- |
| マークアップ | HTML5 | セマンティック構造 |
| スタイリング | Vanilla CSS | ダークテーマ対応、レスポンシブデザイン (`theme.css`: ~45KB, `ranking.css`: ~8KB) |
| スクリプト | Vanilla JavaScript | `app.js`: ~54KB |
| 動的更新 | htmx | ページ遷移なしの部分更新（タブ切替、ランキング切替等） |
| チャート・描画 | Custom Canvas + Plotly.js | Canvas: 株価・出来高チャート / Plotly: 財務グラフ・パターン視覚化 |

### 3.3 AI技術（Hybrid Architecture）
| 項目 | 技術 | 用途 |
| :--- | :--- | :--- |
| メインエンジン | Google Gemini API (`gemini-1.5-flash`) | ニュース和訳・要約、ランキング分析 |
| フォールバック | OpenAI API (`GPT-4o mini`) | Gemini制限時に自動切り替え |
| 株式分析 | GPT-4o | テクニカル・ファンダメンタル総合分析コメント生成 |

---

## 4. データモデル（SQLAlchemy）

### 4.1 実行時テーブル（SQLAlchemy ORM）

| テーブル名 | モデルクラス | 概要 |
| :--- | :--- | :--- |
| `stocks` | `Stock` | ウォッチリスト（code, added_at） |
| `stock_master` | `StockMaster` | 銘柄マスター（code, name, market, updated_at） |
| `app_sync_status` | `AppSyncStatus` | データ同期ステータス管理 |
| `edinet_facts_snapshot` | `EdinetFactsSnapshot` | 正規化済み財務データのスナップショット |
| `edinet_diff_summary` | `EdinetDiffSummary` | 差分比較結果のサマリーキャッシュ |

### 4.2 DDL設計（将来拡張用）
`ddl/create_tables.sql` に以下のテーブルを定義済み（MySQL/InnoDB向け）:

- `stock_master` — 銘柄マスタ
- `stock_prices_daily` — 日次株価データ
- `technical_indicators` — テクニカル指標（SMA, RSI, MACD等）
- `fundamental_data` — ファンダメンタルデータ
- `ai_analysis` — AI分析結果
- `candle_classification` — ローソク足分類結果
- `user_settings` — ユーザー設定
- `watchlist` — ウォッチリスト

---

## 5. 外部API・データソース

| カテゴリ | サービス/API | 用途 |
| :--- | :--- | :--- |
| 市場データ | Yahoo Finance (yfinance) | 株価、指数、ニュース、配当の取得 |
| 銘柄マスター | J-Quants API V2 | 上場銘柄一覧(`/equities/master`)、株価データ(`/equities/bars/daily`)、発行済株式数 |
| 財務サマリー | J-Quants API V2 | 財務サマリー(`/fins/summary`)、配当(`/fins/dividend`) |
| 信用残 | J-Quants API V2 | 信用取引週末残高(`/markets/margin-interest`) ※Free プランでは403 |
| 財務情報 | EDINET API v2 (ZIP/XBRL) | 有価証券報告書の取得、XBRLパース、財務数値抽出 |
| AI / NLP | Google Gemini API | ニュース翻訳・要約、ランキング分析、銘柄影響分析 |
| AI / NLP | OpenAI API | ニュース分析・株式分析のバックアップ、テクニカル/ファンダメンタル総合分析 |

### 5.1 J-Quants API V2 対応

- **公式クライアント**: `jquants-api-client` (v2.0.0) の `ClientV2` クラスを使用。`services/jquants_client.py` が Adapter として機能し、アプリ内の各サービスに統一インターフェースを提供。
- **認証方式**: `x-api-key` ヘッダー（`ClientV2(api_key=...)` で初期化）
- **Free プラン制限対応**:
  - `/equities/master`: 13週前の日付を使用するフォールバック戦略（当日→13週前→直近7日間→固定日付）
  - `/fins/dividend`: 403エラー（Light以上が必要）→ yfinance にフォールバック
  - `/markets/margin-interest`: 403エラー（Free プラン不可）→ フォールバックUI表示
  - レートリミット: 5req/min 対策として0.5秒のスリープ
- **コード正規化**: 4桁→5桁（末尾0付加）、`.T` サフィックス除去
- **戻り値変換**: 公式クライアントが返す pandas DataFrame を `List[Dict]` に変換し、既存コードとの互換性を維持

---

## 6. プロジェクト構成

```
ai-project/
├── app.py                   # Streamlit版エントリーポイント（レガシー）
├── fastapi_app.py           # FastAPI アプリケーション本体
├── database.py              # DB接続・セッション管理
├── requirements.txt         # Python依存パッケージ
├── ai_project.db            # SQLiteデータベースファイル
│
├── models/                  # SQLAlchemy モデル
│   ├── stock.py             # Stock (ウォッチリスト)
│   ├── master.py            # StockMaster, AppSyncStatus
│   ├── edinet_facts_snapshot.py # [NEW] 財務スナップショット
│   └── edinet_diff_summary.py   # [NEW] 差分サマリー
│
├── schemas/                 # [NEW] Pydantic レスポンスモデル
│   └── response_models.py   # JSON API 用型定義
│
├── routers/                 # FastAPI ルーター
│   ├── stocks.py            # 銘柄管理・用語集・ローソク足
│   ├── indices.py           # 主要指標
│   ├── news.py              # ニュース
│   ├── ranking.py           # ランキング
│   ├── fundamental.py       # 個別銘柄ファンダメンタル
│   ├── fundamentals.py      # EDINETファンダメンタルズAPI
│   ├── edinet.py            # EDINET書類API
│   ├── edinet_docs.py       # EDINET書類ダウンロード・解析
│   └── edinet_diff.py       # [NEW] EDINET差分API (htmx)
│
├── services/                # ビジネスロジック
│   ├── stock_service.py     # 銘柄情報・チャート・パターン（94KB）
│   ├── stock_master_service.py # 銘柄マスター同期
│   ├── margin_service.py    # 需給タブ用ロジック（信用残分析）
│   ├── data_fetcher.py      # yfinance データ取得
│   ├── market_indices.py    # 主要指標取得
│   ├── news_service.py      # ニュース取得・AI分析連携
│   ├── ranking_service.py   # ランキング計算・AI解説
│   ├── ai_client.py         # AI連携（Gemini/OpenAI）
│   ├── jquants_client.py    # J-Quants API V2 クライアント（jquants-api-client Adapter）
│   ├── jquants_market_fetcher.py # J-Quantsマーケットデータ取得
│   ├── financial_analyzer.py # ファンダメンタル分析エンジン
│   ├── fundamental_fetcher.py # ファンダメンタルデータ取得
│   ├── fundamental_ratios.py # 投資指標計算(PER/PBR/ROE等)
│   ├── edinet_client.py     # EDINET APIクライアント
│   ├── edinet_service.py    # EDINETサービス統合
│   ├── edinet_fetcher.py    # EDINET書類フェッチ
│   ├── edinet_document_store.py # EDINET書類ストレージ
│   ├── edinet_xbrl_locator.py  # XBRLファイルロケーター
│   ├── edinet_fin_extract.py   # XBRL財務データ抽出
│   └── edinet_diff_service.py  # [NEW] 差分計算ロジック
│
├── utils/                   # ユーティリティ
│   ├── analyzer.py          # テクニカル指標計算（SMA/RSI/トレンド等）
│   ├── candle_classify.py   # ローソク足分類
│   └── chart_pattern_visualizer.py # Plotly パターンチャート生成
│
├── data/                    # 静的データ
│   ├── terms_data.py        # 用語集データ
│   ├── candlestick_terms_data.py # キャンドルパターン用語
│   ├── candle_terms_short.py # 短縮キャンドル用語
│   ├── chart_patterns_data.py # チャートパターンデータ（53種）
│   ├── stock_name_mapper.py # 銘柄名マッピング
│   └── seed_stock_master.json # シードデータ
│
├── templates/               # Jinja2テンプレート
│   ├── base.html            # ベーステンプレート（ヘッダー・ナビ）
│   ├── stocks/              # 銘柄関連
│   │   ├── list.html        # 銘柄一覧
│   │   ├── detail.html      # 銘柄詳細（タブ）
│   │   └── partials/        # 部分テンプレート
│   │       ├── _tab_chart.html       # テクニカル分析タブ
│   │       ├── _tab_fundamental.html # ファンダメンタルタブ
│   │       ├── _tab_dividend.html    # 配当タブ
│   │       ├── _tab_margin.html      # 需給タブ
│   │       └── _tab_shareholder.html # 株主優待タブ
│   ├── indices/index.html   # 指標一覧
│   ├── news/index.html      # ニュース一覧
│   ├── ranking/             # ランキング
│   │   ├── index.html
│   │   └── _list.html       # htmx部分更新用
│   ├── glossary/glossary.html # 用語集
│   ├── candle_patterns/     # ローソク足パターン
│   │   ├── index.html
│   │   └── partials/_list_area.html
│   ├── edinet_search.html   # EDINET検索
│   ├── fundamental_analysis.html # ファンダメンタルレポート
│   └── partials/            # 共通パーツ
│       ├── _candle_modal.html # キャンドルパターンモーダル
│       └── _cross_modal.html  # GC/DCモーダル
│
├── static/                  # 静的アセット
│   ├── css/
│   │   ├── theme.css        # メインCSS（ダークテーマ対応）
│   │   └── ranking.css      # ランキング専用CSS
│   ├── js/
│   │   ├── app.js           # メインJS（チャート描画等）
│   │   └── htmx.min.js      # htmx ライブラリ
│   └── images/              # 画像アセット（78ファイル）
│
├── cache/                   # APIレスポンスキャッシュ
├── ddl/                     # DDL定義（将来拡張用）
├── docs/                    # ドキュメント
│   ├── human/               # 人間向けドキュメント
│   ├── ai/                  # AI/Codex修正ログ
│   ├── architecture/        # アーキテクチャ関連
│   └── security/            # セキュリティ関連
└── tests/                   # テストコード
```

---

## 7. 依存関係（主要ライブラリ）

`requirements.txt` に基づく主要な依存関係です。

### Web関連
- `fastapi >= 0.115.0` — APIフレームワーク
- `uvicorn[standard] >= 0.24.0` — ASGIサーバー
- `jinja2 >= 3.1.2` — HTMLテンプレート
- `python-multipart >= 0.0.6` — フォームデータ処理

### データ分析
- `pandas >= 2.0.0` — データ処理
- `numpy >= 1.24.0` — 数値計算
- `plotly >= 5.17.0` — インタラクティブなグラフ作成

### 金融・データ取得
- `yfinance >= 0.2.28` — Yahoo Financeデータ取得
- `jquants-api-client >= 2.0.0` — J-Quants API V2 公式クライアント
- `edinet-xbrl >= 0.2.0` — EDINETデータパース
- `requests >= 2.31.0` — HTTP通信

### AI / DB / その他
- `google-generativeai >= 0.3.0` — Gemini APIクライアント
- `openai >= 1.3.0` — OpenAI APIクライアント
- `sqlalchemy >= 2.0.0` — ORM/DB接続
- `python-dotenv >= 1.0.0` — 環境変数管理

---

## 8. 環境変数

| 変数名 | 必須 | 概要 |
| :--- | :--- | :--- |
| `JQUANTS_API_KEY` | 推奨 | J-Quants API V2 認証キー |
| `EDINET_API_KEY` | 推奨 | EDINET API 認証キー |
| `GOOGLE_AI_API_KEY` | 推奨 | Google Gemini API キー |
| `OPENAI_API_KEY` | 任意 | OpenAI API キー（フォールバック用） |
| `DATABASE_URL` | 任意 | DB接続先（デフォルト: `sqlite:///./ai_project.db`） |

---

## 9. API エンドポイント一覧

### 9.1 ページ（HTML）

| メソッド | パス | 概要 |
| :--- | :--- | :--- |
| GET | `/` | ホーム（→ /stocks にリダイレクト） |
| GET | `/stocks` | 銘柄一覧 |
| GET | `/stocks/{code}` | 銘柄詳細 |
| GET | `/stocks/{code}/tab/{tab_name}` | タブコンテンツ（htmx） |
| POST | `/stocks/add` | 銘柄追加 |
| POST | `/stocks/delete` | 銘柄削除 |
| GET | `/stocks/{symbol}/fundamental` | 個別ファンダメンタル分析 |
| GET | `/indices` | 主要指標一覧 |
| GET | `/news` | マーケットニュース |
| GET | `/ranking` | ランキングメイン |
| GET | `/ranking/list` | ランキングリスト（htmx） |
| GET | `/glossary` | 用語集 |
| GET | `/candle-patterns` | ローソク足パターン |

### 9.2 API（JSON）

| メソッド | パス | 概要 |
| :--- | :--- | :--- |
| GET | `/api/stocks/search` | 銘柄検索（オートコンプリート） |
| GET | `/api/edinet/documents` | EDINET書類取得 |
| GET | `/api/edinet/health` | EDINETヘルスチェック |
| GET | `/api/edinet/documents/ui/search` | EDINET検索UI |
| GET | `/api/edinet/documents/{doc_id}/download` | 書類ダウンロード・解析 |
| GET | `/api/edinet/documents/{doc_id}/financials` | 財務データ抽出 |
| GET | `/api/fundamentals/reports/{doc_id}` | ファンダメンタルレポート（HTML） |
| GET | `/api/fundamentals/edinet/{doc_id}` | ファンダメンタルデータ（JSON） |
| GET | `/partials/edinet/diff_summary` | EDINET差分サマリー（htmx） |
| GET | `/healthz` | ヘルスチェック |

---

## 10. PM タスク管理指針

> **今後 PM は、アプリに変更が加えられた際に `app_specification.md` を最新の状態に更新するタスクを開発サイクルに含めてください。**
>
> 具体的には：
> 1. 新機能追加・既存機能変更時に、該当セクションを更新すること。
> 2. 新しいエンドポイントの追加時に、セクション9のAPI一覧を更新すること。
> 3. 新しい外部API連携の追加/変更時に、セクション5を更新すること。
> 4. 技術スタックやライブラリの変更時に、セクション3/7を更新すること。
> 5. プロジェクト構成の変更時に、セクション6のディレクトリツリーを更新すること。
