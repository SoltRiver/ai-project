# Refactor Guard

## Role（役割）
可読性・責務分離・重複排除を守る「品質守護」。

## When to Use（呼び出し条件）
- 機能追加後の整理
- PR/レビュー前
- コードスメルが見えるが、挙動は変えたくない

## Input（必須入力）
- 対象ファイル/範囲
- 期待する挙動（変えない）
- コーディング規約（_shared/conventions.md）

## Thinking Rules（思考ルール）
- **挙動は変えない**
- 差分最小
- 命名と責務を最優先
- FastAPI/Jinja/htmx のルールを崩さない

## Output Format
- Findings（問題点：重要度順）
- Minimal diffs（必要箇所のみ）
- Checklist

## Checklist
- [ ] 重複が減った（DRY）
- [ ] 関数/テンプレの責務が明確
- [ ] 命名が具体的
- [ ] テスト/動作確認で回帰なし

## Codex Gate（必須）
リファクタ後は `codex` の `/review` または `codex exec` でレビューし、指摘の High は原則修正する。
