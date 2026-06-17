@echo off
REM ============================================================
REM EDINET DB MCP APIキー登録バッチラッパー
REM
REM 使い方:
REM   set-edinetdb-mcp-key.bat YOUR-API-KEY
REM
REM ※ PowerShell スクリプトのラッパーです。
REM ※ 自作DB（ai_project.db）には影響しません。
REM ============================================================

if "%~1"=="" (
    echo.
    echo [エラー] APIキーを引数で指定してください。
    echo 使い方: %~n0 YOUR-API-KEY
    echo.
    exit /b 1
)

powershell -ExecutionPolicy Bypass -File "%~dp0set-edinetdb-mcp-key.ps1" -ApiKey "%~1"
