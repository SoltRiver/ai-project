# Spring Testing

## Purpose
JUnit / MockMvc 等のテスト方針（参考用）。
※ 本プロジェクトの標準スタックは FastAPI + Jinja2 + htmx。

## Strategy
- Unit: Service のロジック
- Integration: Repository + DB（Testcontainers 等）
- Web: MockMvc で Controller

## Codex Gate（推奨）
テスト追加後に Codex CLI でレビューし、壊れやすさを減らす。
