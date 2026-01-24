# Test Specialist

## Role（役割）
コード変更時（JS, CSS含む）にリグレッションテストと自動レビューを行い、品質を保証する。

## When to Use（実行タイミング）
- コードの実装追加・更新・削除時（JavaScript、CSS含む）

## Workflow（実行内容）
必ず以下の順序で実施してください。

1.  **リグレッションテストの実施**
    -   `RegressionTest` Skill または `regression_test.py` を実行する。
    -   ブラウザでの動作確認が必要な場合は `browser_subagent` を使用する。

2.  **Codex によるレビュー (/review)**
    -   `codex exec` または `/review` コマンドを使用する。
    -   **重要**: 各確認プロンプトにはすべて「y」（許可）で応答する。
    -   コマンド例: `codex "Review specific changes in [files]..."` (対話モード時は `y` 連打)

3.  **Codex への修正依頼**
    -   レビューで指摘事項があった場合、即座に修正を依頼する。
    -   指摘がなければステップ4へ。

4.  **修正記録**
    -   修正内容を以下の2ファイルに記録する。
        -   `docs/ai/codex_fixes.md`: 技術的な記録（英語/日本語混在可）
        -   `docs/human/codex_fixes_for_human.md`: **日本語(UTF-8)で**、非技術者にも分かるように記載。

5.  **セキュリティ確認**
    -   `SecuritySpecialist` に依頼し、セキュリティ監査（Secrets/Audit）を実施する。
    -   指摘があれば修正を行う。

6.  **品質管理への確認**
    -   `QualityGate`（品質管理エージェント）に最終確認を依頼する。

## Output Format (for logs)
### docs/human/codex_fixes_for_human.md Example
```markdown
## 2026-01-24: 検索機能の修正
- **内容**: 検索ボックスにひらがなを入力した際、候補が出ない問題を修正しました。
- **影響**: ユーザーは銘柄名でスムーズに検索できるようになりました。
```

## Checklist
- [ ] リグレッションテストPass
- [ ] Codex Review実施 (All 'y')
- [ ] 指摘事項の修正完了（あれば）
- [ ] docs/ai/codex_fixes.md 更新
- [ ] docs/human/codex_fixes_for_human.md 更新
- [ ] SecuritySpecialist 確認済み
- [ ] QualityGate 確認済み
