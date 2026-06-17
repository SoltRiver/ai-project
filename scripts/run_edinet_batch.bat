@echo off
REM =====================================================
REM EDINET 日次バッチ 自動実行ラッパー
REM タスクスケジューラから呼び出される
REM =====================================================

REM プロジェクトディレクトリに移動
cd /d "c:\Users\curem\ai-project"

REM ログ出力先
set LOG_DIR=c:\Users\curem\ai-project\logs
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

REM タイムスタンプ付きログファイル名
for /f "tokens=1-3 delims=/ " %%a in ('date /t') do set DATESTAMP=%%c%%a%%b
for /f "tokens=1-2 delims=: " %%a in ('time /t') do set TIMESTAMP=%%a%%b
set LOGFILE=%LOG_DIR%\edinet_batch_%date:~0,4%%date:~5,2%%date:~8,2%.log

REM .env を読み込むため、Python側で dotenv を使用
REM バッチ実行（100リクエスト/日）
echo [%date% %time%] EDINET Daily Batch Starting... >> "%LOGFILE%" 2>&1
python scripts/edinet_daily_batch.py >> "%LOGFILE%" 2>&1
echo [%date% %time%] EDINET Daily Batch Finished. Exit code: %ERRORLEVEL% >> "%LOGFILE%" 2>&1
