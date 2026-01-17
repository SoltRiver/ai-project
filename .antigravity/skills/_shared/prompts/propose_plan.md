# Propose Plan Prompt

目的：
実装前に「差分最小」「影響範囲最小」「回帰防止」を満たす計画を提示し、手戻りを減らす。

---

## いつ使うか
- 新機能追加
- 複数ファイルにまたがる修正
- DB/外部連携/権限が絡む
- UX/UI の変更がある（a11y 含む）

---

## 出力フォーマット
1. Summary（目的と結論）
2. Scope（触る/触らない）
3. Design（SSR + htmx 前提、更新境界、状態）
4. Config Plan（外部連携/API設定の集約：settings.py/config.py）
5. Static Assets Plan（CSS/JS/画像は static 外出し）
6. Reuse Plan（関数/定数/テンプレmacroで重複削減）
7. Tests（追加/更新するテスト）
8. Rollback / Risks（破壊的変更がないか）
9. Codex Gate（レビュー→修正→検証→commit/push）

---

## Codex Gate（必須）
- 実装後：Codex CLI でレビュー → 指摘修正
- 検証後：commit & push
- 提出：最終diff + チェックリスト（_shared/output_format.md）
