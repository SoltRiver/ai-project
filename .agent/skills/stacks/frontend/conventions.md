# Frontend Conventions (Reference)

## Purpose
一般的なフロントエンド規約（参考用）。
※ 本プロジェクトでは SPA/ビルドツール/JSライブラリは禁止。

## Allowed (this project)
- HTML/CSS（テンプレは Jinja2）
- htmx（部分更新）
- Minimal vanilla JS（ESC、フォーカス復帰など補助のみ）

## Forbidden
- React/Vue/Svelte/Next 等
- npm 依存、バンドラ、UI ライブラリ

## Codex Gate（推奨）
フロント変更後は Codex CLI でレビューし、a11y と回帰を確認する。
