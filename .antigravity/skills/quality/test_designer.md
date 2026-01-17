# Test Designer

## Role（役割）
要件と実装に対して、**抜け漏れのないテスト観点**を設計し、実行可能なテスト（単体/統合）へ落とす。

## When to Use（呼び出し条件）
- 新規機能追加、既存機能の仕様変更
- バグ修正後（再発防止テストが必要）
- クリティカルな業務処理（決済/権限/データ更新）

## Input（必須入力）
- 仕様（受け入れ条件、画面/API、入力項目と制約）
- 変更差分（diff または対象ファイル一覧）
- 既存テストの有無（pytest 等）
- Tech Stack 制約（FastAPI + Jinja2 + htmx、最小JS）

## Thinking Rules（思考ルール）
- **サーバ側バリデーション/権限制御を最優先でテスト**する
- 正常系だけでなく、**境界値・異常系・権限・同時実行**を必ず含める
- UI は E2E に寄せ過ぎず、**サービス/ルートの統合テスト**で担保する
- テストは「壊れやすい実装依存」より「仕様依存」を優先する

## Output Format（_shared/output_format.md に準拠）
1. Summary
2. Test Strategy（どこをどの層で担保するか）
3. Test Cases（表：観点/入力/期待結果/優先度）
4. Suggested Tests（pytest などの骨子。必要なら diff）
5. Codex Review Report（テスト追加後）
6. Checklist / Risks

### Test Cases（テンプレ）
| Priority | Target | Scenario | Input | Expected |
|---|---|---|---|---|
| High | API | 権限なしで更新 | ... | 403 |
| High | API | バリデーション | ... | 422 + message |
| Med | UI | 一覧の空状態 | ... | Empty state UI |

## Checklist
- [ ] 正常/異常/境界値が揃っている
- [ ] 権限（誰が何をできるか）をテストしている
- [ ] バグ修正なら再発防止テストがある
- [ ] テストは差分最小で追加されている

## Codex Gate（必須）
テスト追加/更新後は Codex CLI でレビューし、壊れやすいテストや冗長な前処理があれば修正する。
