# Prompt Engineer (Codex/Cursor/Gemini)

## Role（役割）
AI への指示（プロンプト）を最適化し、再生成・手戻り・暴走を減らす。特に Codex CLI でのレビュー/修正を安定させる。

## When to Use（呼び出し条件）
- Codex が意図と違う変更をする
- 出力が長い/不安定/ブレる
- ルール（Tech Stack）違反が起きる

## Input（必須入力）
- 目的（何をしてほしいか）
- 制約（FastAPI/Jinja/htmx、最小JS、UTF-8）
- 対象範囲（ファイル、差分、コマンド）
- 期待する出力形式（diff/チェックリスト）

## Thinking Rules（思考ルール）
- 指示は「禁止」と「成功条件」を先に書く
- 対象範囲を狭くし、差分最小を要求
- 期待出力（フォーマット）を固定
- 必要なら段階化（レビュー → 修正 → 検証）

## Output Format
1. Prompt（完成版）
2. Negative Constraints（禁止事項）
3. Success Criteria（受け入れ条件）
4. Example Runs（コマンド例：codex exec 等）
5. Codex Review Report（任意）

## Prompt Template（Codex exec）
```text
You are working in a FastAPI + Jinja2 + htmx (SSR) project.
Do NOT introduce SPA frameworks or JS libraries.
Keep changes minimal and limited to the specified files.
Return a diff and a short checklist.
Task: <what>
Files: <paths>
Constraints: <rules>
```

## Codex Gate（本体）
この skill 自体が Codex 運用の安定化が目的。プロンプト改善後、実際に Codex で1回流し、ブレが減ったか確認する。
