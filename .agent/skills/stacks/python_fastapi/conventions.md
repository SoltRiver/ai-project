# FastAPI Conventions (SSR + Jinja2 + htmx)

## Purpose
本プロジェクト（FastAPI + Jinja2 + htmx）用の実装規約。

## Must（必須）
- SSR 優先（テンプレでレンダリング）
- htmx は部分更新に限定（状態管理しない）
- JS は最小（ライブラリ禁止）
- ルーティングとテンプレの対応を明確にする

## Project Rules Addendum
- a11y: フォーカス/コントラスト/ラベル/キーボード操作を必須化
- static: CSS/JS/画像は `static/` 配下へ外出し（テンプレ内に巨大な埋め込み禁止）
- config: 外部連携/APIキー等は `settings.py`/`config.py` に集約
- reuse: 関数/テンプレ macro で重複削減（過剰抽象化は禁止）
