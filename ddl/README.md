# DDLファイル説明

このディレクトリには、株価分析アシスタントのデータベーススキーマ定義（DDL）が含まれています。

## ファイル構成

- `create_tables.sql`: すべてのテーブル定義を含むDDLファイル

## テーブル一覧

### 1. stock_master
銘柄マスタテーブル。銘柄の基本情報を格納します。

### 2. stock_prices_daily
日次の株価データ（OHLC、出来高）を格納します。

### 3. technical_indicators
テクニカル指標（移動平均線、RSI、MACDなど）を格納します。

### 4. fundamental_data
ファンダメンタルデータ（PER、PBR、配当利回りなど）を格納します。

### 5. ai_analysis
AI分析結果を格納します。

### 6. candle_classification
ローソク足の分類結果を格納します。

### 7. user_settings
ユーザー設定を格納します（将来拡張用）。

### 8. watchlist
ウォッチリストを格納します（将来拡張用）。

## 使用方法

MySQLまたはMariaDBで実行してください：

```bash
mysql -u username -p database_name < create_tables.sql
```

または、MySQLクライアントで：

```sql
SOURCE create_tables.sql;
```

## 注意事項

- このDDLは将来のデータ永続化機能を想定したものです
- 現在のアプリケーションはデータベースを使用していません（yfinanceから直接取得）
- データベースを使用する場合は、各モジュールにデータベース接続機能を追加する必要があります

