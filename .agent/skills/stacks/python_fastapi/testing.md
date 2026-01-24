# FastAPI Testing (pytest)

## Purpose
FastAPI + SSR + htmx プロジェクトでのテスト戦略。

## Strategy
- Unit: services / utils の純粋関数・ロジック
- Integration: router + dependency（DB を含む場合はテストDB）
- Template: 重要テンプレはスモーク（レンダリング）で落ちないことを確認
- Security: 権限/CSRF/入力検証

## Minimal Recommendations
- 主要ルートの 200/302/403/422 を押さえる
- バグ修正には必ず回帰テストを追加

## Codex Gate（必須）
テスト追加/更新後、Codex CLI でレビューし、壊れやすいテストや過剰モックを修正する。
