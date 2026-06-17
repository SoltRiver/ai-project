import sys
import os
import subprocess
import threading
from playwright.sync_api import sync_playwright

# testsディレクトリの親ディレクトリ（プロジェクトルート）をパスに追加してインポート可能にする
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.utils import wait_for_server

# 定数定義 (Commonization)
PORT = 8001
BASE_URL = f"http://localhost:{PORT}"
INDICES_URL = f"{BASE_URL}/indices"
SCREENSHOT_FILENAME = "indices_screenshot.png"
# プロジェクトルートからの相対パスで保存
SCREENSHOT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), SCREENSHOT_FILENAME
)


def run_test():
    print("Uvicornサーバーを起動しています...")
    # サーバーをバックグラウンドで起動
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "fastapi_app:app", "--port", str(PORT)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        print(f"ポート {PORT} でサーバーの起動を待機しています...")
        if not wait_for_server(PORT):
            print("サーバーへの接続に失敗しました。")
            return

        print("サーバーの準備が完了しました。Playwrightを起動します...")

        with sync_playwright() as p:
            # ブラウザ起動
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # 指標ページへ移動
            print(f"{INDICES_URL} へ遷移しています...")
            response = page.goto(INDICES_URL)

            # レスポンス確認
            if response.status != 200:
                print(f"ページの読み込みに失敗しました: ステータス {response.status}")
            else:
                print("ページの読み込みに成功しました。")

            # スクリーンショット撮影
            page.screenshot(path=SCREENSHOT_PATH)
            print(f"スクリーンショットを保存しました: {SCREENSHOT_PATH}")

            # コンテンツの検証
            content = page.content()

            checks = ["日経平均", "NYダウ", "NASDAQ", "主要指標一覧", "主要指標"]
            for text in checks:
                if text in content:
                    print(f"[OK] ページ内に '{text}' が見つかりました。")
                else:
                    print(f"[FAIL] ページ内に '{text}' が見つかりませんでした。")

            # テーブル行数の確認
            rows = page.locator("table.stock-table tbody tr").count()
            print(f"テーブル内の行数: {rows}")

            if rows >= 3:
                print("[OK] テーブルにデータが表示されています。")
            else:
                print("[FAIL] テーブルの行数が少なすぎます。")

            browser.close()

    except Exception as e:
        print(f"テスト実行中にエラーが発生しました: {e}")
    finally:
        print("サーバーを停止しています...")
        process.terminate()
        # プロセスの終了を確実に待機
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        print("テストシーケンスが終了しました。")


if __name__ == "__main__":
    run_test()
