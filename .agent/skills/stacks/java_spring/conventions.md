# Java Spring Conventions

## Purpose
Spring Boot プロジェクト向けの規約（参考用）。
※ 本プロジェクトの標準スタックは FastAPI + Jinja2 + htmx。Spring は別案件用。

## Conventions
- Controller/Service/Repository の責務を明確化
- DTO と Entity を分ける
- Validation は Bean Validation を基本
- 例外は GlobalExceptionHandler に集約

## Codex Gate（推奨）
Spring 案件で利用する場合、実装後に Codex CLI でレビュー & 修正を行う。
