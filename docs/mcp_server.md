# EDINET DB MCPサーバー ドキュメント

## 概要

EDINET DBに蓄積された銘柄・財務情報を、[Model Context Protocol (MCP)](https://modelcontextprotocol.io/) 経由でAIエージェントから取得可能にするサーバーです。

### データ取得の優先順位

全ツールにおいて以下の優先順位でデータを取得します：

1. **EDINET DB** — ローカルDBに蓄積されたキャッシュ・処理済みデータ
2. **既存の取得処理** — yfinance, j-Quants, EDINET API 等へのフォールバック

## セットアップ

### 1. 依存パッケージのインストール

```bash
pip install mcp
```

### 2. MCPサーバーの起動確認

```bash
python mcp_server.py
```

### 3. Claude Desktop / Cursor への登録

`mcp_config_example.json` を参考に、MCPクライアントの設定に追加してください。

**Claude Desktop** の場合：
- `%APPDATA%\Claude\claude_desktop_config.json` に以下を追加

```json
{
  "mcpServers": {
    "edinet-db": {
      "command": "python",
      "args": ["c:\\Users\\curem\\ai-project\\mcp_server.py"]
    }
  }
}
```

**Cursor** の場合：
- Settings → MCP Servers から追加

### 4. MCPインスペクタでの確認（任意）

```bash
mcp dev mcp_server.py
```

## 利用可能なツール一覧

### 1. `search_company` — 企業検索

銘柄コードまたは企業名でEDINET DB内の企業情報を検索します。

| パラメータ | 型 | 必須 | 説明 |
|---|---|---|---|
| `query` | string | ✅ | 銘柄コード（例: "7203"）または企業名の一部（例: "トヨタ"） |

### 2. `get_company_filings` — 書類一覧

指定銘柄のEDINET提出書類一覧を取得します。

| パラメータ | 型 | 必須 | 説明 |
|---|---|---|---|
| `stock_code` | string | ✅ | 銘柄コード（例: "7203"） |
| `doc_type` | string | ❌ | 書類種別コード。"120"=有報, "140"=四半期 |
| `limit` | int | ❌ | 取得件数（デフォルト: 10） |

### 3. `get_financial_highlights` — 財務ハイライト

指定書類の財務ハイライト（売上高、営業利益、純利益等）を取得します。

| パラメータ | 型 | 必須 | 説明 |
|---|---|---|---|
| `doc_id` | string | ✅ | EDINET書類ID（例: "S100TR7I"） |

### 4. `get_financial_diff` — 前年度比較差分

指定書類と前年度の差分比較データ（固定6指標＋変化大3件）を取得します。

| パラメータ | 型 | 必須 | 説明 |
|---|---|---|---|
| `doc_id` | string | ✅ | EDINET書類ID |
| `force_regenerate` | bool | ❌ | キャッシュを無視して再生成するか |

### 5. `get_financial_timeseries` — 時系列データ

指定銘柄の財務指標の年次推移データを取得します。

| パラメータ | 型 | 必須 | 説明 |
|---|---|---|---|
| `stock_code` | string | ✅ | 銘柄コード |
| `metric_key` | string | ❌ | 指標キー（例: "revenue", "operating_profit"） |

### 6. `get_xbrl_facts` — XBRLファクト検索

指定書類のXBRL生データを検索・取得します。

| パラメータ | 型 | 必須 | 説明 |
|---|---|---|---|
| `doc_id` | string | ✅ | EDINET書類ID |
| `concept` | string | ❌ | コンセプト名でフィルタ（部分一致） |
| `limit` | int | ❌ | 取得件数上限（デフォルト: 50） |

### 7. `get_derived_metrics` — 派生指標

指定書類の派生指標（ROE、自己資本比率等）を取得します。

| パラメータ | 型 | 必須 | 説明 |
|---|---|---|---|
| `doc_id` | string | ✅ | EDINET書類ID |

### 8. `get_documents_by_date` — 日次書類一覧

指定日に提出された全書類を一覧表示します。

| パラメータ | 型 | 必須 | 説明 |
|---|---|---|---|
| `target_date` | string | ✅ | 対象日（YYYY-MM-DD形式） |
| `doc_type` | string | ❌ | 書類種別コードでフィルタ |
| `limit` | int | ❌ | 取得件数上限（デフォルト: 50） |

### 9. `get_ai_summary` — AI要約

指定銘柄のAI生成要約（SNAPSHOT/DELTA）を取得します。

| パラメータ | 型 | 必須 | 説明 |
|---|---|---|---|
| `stock_code` | string | ✅ | 銘柄コード |
| `year` | int | ❌ | 対象年度（省略時は最新） |

### 10. `get_stock_overview` — 銘柄総合情報

銘柄の総合情報を一括取得します（企業情報 + 最新財務 + 派生指標 + 差分）。

| パラメータ | 型 | 必須 | 説明 |
|---|---|---|---|
| `stock_code` | string | ✅ | 銘柄コード |

## 書類種別コード一覧（主要）

| コード | 種別 |
|---|---|
| `120` | 有価証券報告書 |
| `130` | 訂正有価証券報告書 |
| `140` | 四半期報告書 |
| `150` | 訂正四半期報告書 |
| `160` | 半期報告書 |

## トラブルシューティング

### サーバーが起動しない

- `python mcp_server.py` を直接実行してエラーメッセージを確認してください
- `.env` ファイルが存在し、必要な環境変数が設定されているか確認してください
- `pip install mcp` が正常に完了しているか確認してください

### データが取得できない

- EDINET DB （`ai_project.db`）にデータが蓄積されているか確認してください
- EDINET DB にデータがない場合、フォールバック先の yfinance / EDINET API が正常に動作するか確認してください
