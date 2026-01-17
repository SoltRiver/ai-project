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

## Git Workflow（必須）
- 実装が完了し次第、速やかにコミット & プッシュを行う
- コミットの単位は論理的な機能ブロックごとに行う
- **コミット前には `codex` コマンドでコードレビューを実施し、修正点を反映する**
- **修正点がある場合は、可能な限り `codex` に自動修正（fix）を行わせる**

