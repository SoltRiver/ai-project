# Output Format

## Purpose
Antigravity の出力を「レビューしやすく・再利用可能」に統一します。

---

## Default Output Order
1. Summary（何をしたか・なぜ）
2. Findings / Analysis（根拠）
3. Proposal or Patch（提案 or diff）
4. Codex Review Report（Codex の指摘と対応）
5. Verification（テスト/手動確認）
6. Git Commit & Push（コミット/プッシュ結果）
7. Checklist（確認項目）
8. Risks / Notes（残リスク）

---

## Code Changes
必ず diff 形式（最小差分）で提示：

```diff
- old
+ new
```

---

## Codex Review Report（必須）
以下のどちらかを必ず含める：
- `/review` の結果サマリ（重要度順）
- `codex exec` によるレビュー結果と、対応内容

形式：
- Issue（重要度）: 概要
  - 対象: file:line（可能なら）
  - 対応: 直した/見送り（理由）
  - 追加確認: テスト/手動確認

---

## Git Commit & Push（必須：修正完了時）
- コミットメッセージ
- push 先ブランチ
- CI 結果（あれば）

例：
- Commit: `fix: address codex review findings`
- Branch: `feature/xxx`
- Push: `origin feature/xxx`
- CI: passed / skipped（理由）

---

## Planning / Design
Markdown 構造のみ（過剰装飾しない）：
- 見出し
- 箇条書き
- 必要なら表

---

## Forbidden Output
- 変更理由の説明なし
- フォーマットが毎回変わる
- Codex レビュー結果がない
- コミット/プッシュ情報がない（修正完了時）

---

## Universal Checklist Items（固定）
以下は **全ての変更で毎回チェック**する（対象外なら「対象外理由」を明記）。

- [ ] a11y（コントラスト/フォーカス可視化/ラベル・ARIA/キーボード操作）
- [ ] 色だけで状態を伝えていない（文言/形/アイコン等の併用）
- [ ] 静的ファイル（CSS/JS/画像）が `static/` に外出しされている
- [ ] テンプレ内に巨大な `<style>` / `<script>` を埋め込んでいない
- [ ] 外部連携/API設定が `settings.py` / `config.py` に集約されている
- [ ] 再利用（関数/変数/テンプレ macro）で重複が減っている（過剰抽象化なし）
- [ ] Tech Stack 違反がない（SPA/ビルドツール/JSライブラリ禁止）
- [ ] Codex Review Report を含めた
- [ ] 修正完了時は Commit & Push を行った

