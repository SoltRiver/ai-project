# Security Audit Skill

本スキルは、サイバー攻撃を想定した観点で「コード・設定・運用」にセキュリティ上の問題がないかをチェックする。

## 想定する攻撃者
- 外部からの不正アクセス
- 認証情報の窃取
- XSS / SQL Injection / SSRF
- APIの不正利用
- 設定ミスによる情報露出

## 対象
- FastAPI / Python バックエンド
- Jinja2 テンプレート
- htmx / 最小JS
- systemd / Docker / CI 設定

## Checking Points（主なチェックポイント）
### 1. Injection
- SQL: ORMやパラメータバインドを使用しているか
- OS Command: `shell=True` を避けているか

### 2. XSS (Cross Site Scripting)
- Jinja2: `| safe` フィルタを安易に使用していないか
- User Input: ユーザー入力をそのままHTMLに出力していないか

### 3. Authentication / Authorization
- エンドポイントに適切な保護（認証・認可）があるか
- パスワード強度は十分か、ハッシュ化されているか

### 4. Configuration
- Debugモードが本番で無効化されているか
- エラー詳細がクライアントに露出していないか

## Checklist
- [ ] インジェクション対策（SQL/Command）
- [ ] XSS対策（エスケープ処理）
- [ ] 認証・認可の不備がないか
- [ ] デバッグ情報の露出がないか
