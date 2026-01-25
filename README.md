# 株価チャートアシスタント (FastAPI + htmx)

 FastAPI + Jinja2 + htmx で株価リスト/詳細をサーバーサイドレンダリングする構成です。既存のデータ取得・分析ロジック (yfinance, pandas, analyzer など) を再利用し、最小限の JS でタブ切り替えを実装しています。Streamlit 版は廃止し、`app.py` は FastAPI 版への案内のみとなっています。

## セットアップ
1. Python 環境を用意し、`pip install -r requirements.txt`
2. (任意) AI コメントを使う場合は `OPENAI_API_KEY` を設定

## 起動
```bash
uvicorn fastapi_app:app --reload --port 8000
```
ブラウザで `http://localhost:8000/stocks` にアクセスします。

## 画面構成
- `/stocks` : 株価リスト。銘柄名(コード) / 現在値 / 変動額(率) / 最高値・最安値の4列。
- `/stocks/{code}` : 株価詳細。タブで「チャート / ファンダメンタル分析 / 配当 / 株主優待」を切替。初期表示でチャートタブを自動ロード。
- `/glossary` : 用語辞典。PER, PBR, トレンドなど一般用語を初心者向けコメント付きで掲載。
- `/candle-patterns` : ローソク足パターン。ローソク足パターンを独立したページで解説。

## 実装メモ
- SSR: Jinja2 Templates (`templates/`)
- タブ更新: htmx (base で読み込み) / `hx-target="#tab-content"`
- データ: `services/stock_service.py` が yfinance ベースの取得を集約。`data_fetcher.py` / `fundamental_fetcher.py` / `candle_classify.py` を利用。
- テーマ: `static/css/theme.css` + `static/js/app.js` でライト/ダーク切り替え。
- 静的資産: `static/js/htmx.min.js` を同梱。
- ルーター: `routers/stocks.py` に `/stocks`, `/stocks/{code}`, `/stocks/{code}/tab/{tab_name}` を集約。

## テスト/確認
- `uvicorn fastapi_app:app --reload` で起動し、リスト→詳細タブの遷移を確認。
- yfinance へのネットワークが届かない場合は画面上で "N/A" 表示になります。

## �f�B���N�g���\��
�ڍׂ� [docs/architecture/directory_structure.md](docs/architecture/directory_structure.md) ���Q�Ƃ��Ă��������B

- **data/**: �萔�����f�[�^
- **services/**: �r�W�l�X���W�b�N
- **utils/**: �ėp���W�b�N
- **scripts/**: ���؃f�o�b�O�p�X�N���v�g
