---
description: 品質管理チェック：パターン画像の表示確認
---

# 画像表示確認ワークフロー

ローソク足パターンやその他のカード表示に使用される画像（SVG/PNG）が
正しくブラウザ上で表示されていることを確認するためのワークフローです。

## 前提条件
- Uvicorn サーバーが起動していること
- ブラウザサブエージェントが利用可能であること

## チェック手順

1. **SVGファイルの存在確認**
   - `stock_service.py` の `CANDLE_PATTERN_CARDS` に定義されている全パターンの `svg` プロパティを抽出する。
   - 各SVGファイルが `static/` ディレクトリ内に実際に存在するか確認する。
   // turbo

2. **ブラウザでの画像表示確認**
   - `/candle-patterns` ページにアクセスする。
   - JavaScript を使い、全ての `<img>` タグの `naturalWidth` を取得する。
   - `naturalWidth === 0` のものがあれば「画像読み込み失敗」として報告する。

3. **壊れた画像の一覧出力**
   - 読み込み失敗した画像の `src` と `alt` を一覧表示する。
   - 失敗がゼロなら「全画像OK」と判定する。

## 判定基準
- **PASS**: 全パターンの画像が存在し、ブラウザ上で正常に表示される。
- **FAIL**: 1つ以上の画像が見つからない、または表示されていない。

## 関連ファイル
- `services/stock_service.py` - パターン定義（`svg` プロパティ）
- `static/images/candle_patterns/` - SVG画像ファイル
- `templates/candle_patterns/partials/_list_area.html` - 表示テンプレート
