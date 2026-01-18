# Conventions

## Purpose
命名・構成・例外方針を統一し、コードとテンプレの保守性を上げます。

---

## Naming
- Python / ファイル: `snake_case`
- HTML id / class: `kebab-case`
- 明示的で短すぎない名前を優先

---

## Directory Rules（FastAPI + Jinja2 + htmx）
- `templates/pages/` : ルーティングに対応するページ
- `templates/partials/` : htmx 差し替え断片（返却HTMLの最小単位）
- `templates/components/` or `templates/macros/` : 再利用 UI
- partial を「細かくしすぎ」ない（境界が崩れる）

---

## Exception Handling
- 例外は握りつぶさない
- ユーザー向けメッセージとログを分離
- スタックトレース/内部情報を UI に出さない

---

## Documentation
- README は「最初に読む人」向け
- コメントは **なぜ** を書く（what ではなく why）

---

## Static Assets Rule（必須）
- CSS/JS/画像は **外部ファイル**として `static/` 配下へ配置する
- テンプレ内の `<style>`/`<script>` は「極小の例外」を除き禁止
- JS は補助用途のみ（ESCで閉じる、フォーカス復帰など）
- **静的ファイル（CSS, JavaScript, Images）へのアクセス及び更新は常に許可する**

---

## Config Centralization（必須）
- API 情報/外部連携設定/環境変数は **1箇所に集約**する
  - 例：`app/config.py` または `app/settings.py`（Pydantic Settings）
- ルートやサービスに散らさない（影響範囲を小さくする）

---

## Reusability（必須・ただし過剰抽象化禁止）
- 重複は関数/クラス/テンプレ macro にまとめる
- 変数や定数を活用し、マジックナンバー/文字列を減らす
- ただし「将来のため」だけの抽象化は入れない（必要最小）

---

## Accessibility（必須）
- フォーカス可視化、キーボード操作、label/aria、コントラストを満たす
- 色だけで状態を表現しない（文言/アイコン/形状も併用）

---


---

## UI/UX Design Guidelines（必須）
- **視線移動（Gaze Flow）を配慮する**
  - 重要な情報（ステータス、現在値、アクションボタン）は左上〜中央、またはZ型/F型のライン上に配置する
  - 関連する情報は近接させ（Proximity）、視線のジャンプを減らす
  - ユーザーの視線が迷わないよう、強弱（Visual Hierarchy）を明確にする（フォントサイズ、色、余白）

---

## Git Workflow（必須）
- 実装が完了し次第、速やかにコミット & プッシュを行う
- コミットの単位は論理的な機能ブロックごとに行う
- **実装完了後、速やかに `codex` コマンドを実行し、対話モードで `/review` コマンドを入力してレビューを実施する**
- **許可を求められた場合は、すべて `Yes` と回答する**
- **レビューの結果、エラーや修正点が検出された場合は、コミット・プッシュを行わず、`codex` に修正を依頼する**
- **修正完了後、再度レビューを行い、問題がなければコミット & プッシュを行う**
- **GitHubにプッシュまで完了したら、`docs/ai/stock_analysis_requirements.md` の更新を日本語で行う**

