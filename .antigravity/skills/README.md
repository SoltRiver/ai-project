# Antigravity Skills

このディレクトリは Antigravity の skills 一式です。

## Global Rules（重要）
- Tech Stack: FastAPI / Jinja2 / htmx（最小JS、ライブラリ禁止）
- SSR 優先、UTF-8 統一
- **実装後は Codex CLI によるレビュー & 修正が必須**（_shared/policies.md 参照）
- **修正完了後はブランチにコミット & プッシュが必須**（_shared/policies.md 参照）

## Standard Workflow（推奨運用）
1. Plan（必要なら）: `_shared/prompts/propose_plan.md`
2. Implement（差分最小）
3. Review & Fix with Codex（必須）
   - `codex` の `/review` または `codex exec` で指摘 → 修正
4. Verify（テスト/手動確認）
5. Commit & Push（必須）
   - `git add <paths>` → `git commit -m "..."` → `git push origin <branch>`
6. Finalize（提出フォーマット）: `_shared/prompts/finalize_patch.md`

## Where to start
- まずは `_shared/` と `core/` を参照してください。
