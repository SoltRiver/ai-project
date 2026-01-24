# Policies

## Purpose
全ての skill が従う「最上位ルール」。
品質事故・設計崩壊・過剰実装を防ぎます。

---

## Absolute Rules（最優先）
- **破壊的変更は禁止**
  - DB スキーマ、API、テンプレ構造の破壊は明示的許可なしに行わない
- **プロジェクト Tech Stack を破らない**
  - FastAPI / Jinja2 / htmx のみ
  - SPA・ビルドツール禁止（React/Vue/Next 等）
  - JS は最小限のプレーン JS のみ（ライブラリ禁止）
- **SSR を最優先**
  - JS や htmx でしか成立しない設計は禁止（ただし UX 改善の部分更新は可）
- **UTF-8 固定**
- **推測で仕様を作らない**
  - 不明点は `prompts/ask_clarify.md` を優先

---

## Additional Engineering & UX Rules（追加条件）
- **UX/UI はアクセシビリティに配慮**すること
  - コントラスト、フォーカス可視化、キーボード操作、ラベル/ARIA を考慮
  - 色だけで状態を伝えない（形/文言/アイコン等も併用）
- **静的ファイル（CSS/JS/画像）は外部ファイルとして管理**すること
  - テンプレ内の巨大な `<style>`/`<script>` を避け、`static/` 配下へ
  - JS は最小限（ライブラリ禁止）で、必要なときのみ外部 JS を追加
- **API 情報や外部連携設定は集中管理**し、影響範囲を小さくすること
  - 例：`settings.py`（Pydantic Settings）や `config.py` に集約
  - ルートやサービス内に散らさない
- **再利用可能な設計を優先**すること
  - 変数/関数/テンプレ macro（Jinja2）を活用し重複を減らす
  - ただし過剰抽象化は禁止（必要最小の再利用）

---

## Required: Post-Implementation Review with Codex CLI（実装後レビュー必須）
実装（または修正）を行った後は、**Codex CLI によるレビュー & 修正**を実施し、
問題があればその場で修正します。

### 推奨フロー（ローカル）
1. 変更点を保存（コミット前でOK）
2. Codex でレビュー（対話 or exec）
3. 指摘を反映（Codex に修正させる）
4. テスト/静的チェック（プロジェクトが持つ範囲で）
5. 最終 diff とチェックリストを提出

### 例：非対話（exec）でレビュー & 修正
```bash
# レビュー（指摘のみ）
codex exec "Review the current changes. Focus on correctness, security, and maintainability. Output a prioritized list of issues with file:line references when possible. Do not change files."

# 修正（指摘を反映）
codex exec "Fix the issues you found in the review. Keep changes minimal. Do not introduce SPA frameworks or JS libraries. Prefer server-side fixes. After edits, run available tests/lint commands and report results."

---

## Required: After Fix, Commit & Push（修正後のコミット＆プッシュ必須）
Codex の指摘反映・テスト確認が完了したら、**対象ブランチにコミット＆プッシュ**して変更を確定します。

### 推奨フロー
1. `git status` で差分確認
2. スコープを絞ってステージング（`git add <paths>`）
3. コミット（メッセージは規約に従う）
4. `git push`（対象ブランチ）

### コマンド例
```bash
git status
git add <paths>
git commit -m "fix: address review feedback"
git push origin <branch>
```

### ルール
- コミットは **差分最小**で、意図が分かる単位にする
- 破壊的変更や大規模整形は別コミットに分離
- CI がある場合は、可能な範囲で成功を確認してからプッシュする

---

## Decision Priority（判断順位）
1. 正確性（Correctness）
2. 保守性（Maintainability）
3. 一貫性（Consistency）
4. 可読性（Readability）
5. パフォーマンス（Performance）

---

## Forbidden Behaviors
- 「とりあえず動く」コードの提出
- 不要な抽象化・パターン導入
- 指示されていないファイルの修正
- 黙って仕様を増やす
- **Codex レビューを省略すること**
- **コミット＆プッシュを省略すること**（修正完了時）

---

## Required Mindset
- 常に **差分最小**
- **説明責任を持つ（なぜこの変更か）**
- 出力は「人間レビュー前提」
