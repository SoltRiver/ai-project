import sys
import os
import time
from multiprocessing import Process
import uvicorn
from playwright.sync_api import sync_playwright

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_server():
    """Uvicornサーバーを起動する (subprocess使用)"""
    # この関数はProcessではなく、verify_browser内で直接subprocessとして呼ぶ
    pass

def verify_browser():
    """ブラウザでニュースページを確認する"""
    # サーバーをサブプロセスとして起動
    import subprocess
    print("サーバーを起動しています...")
    # .envを読み込むためにpython -m uvicornを使用
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "fastapi_app:app", "--host", "127.0.0.1", "--port", "8001"],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    try:
        print("サーバーの起動を待機しています...")
        time.sleep(5)  # サーバー起動待ち

        with sync_playwright() as p:
            print("Playwrightを起動します...")
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # トップページから遷移確認
            url = "http://localhost:8001/indices" # スタート地点
            print(f"{url} へ遷移しています...")
            page.goto(url)
            
            # リンク確認
            news_link = page.get_by_role("link", name="ニュース")
            if news_link.is_visible():
                print("[OK] 'ニュース' リンクが見つかりました。")
                news_link.click()
                page.wait_for_url("**/news")
                print("ニュースページへ遷移しました。")
            else:
                print("[ERROR] 'ニュース' リンクが見つかりません。")
                return

            # ニュースページのコンテンツ確認
            title = page.locator("h1").text_content()
            if "マーケットニュース" in title:
                print(f"[OK] ページタイトル確認: {title}")
            
            # ニュースカード確認
            cards = page.locator(".news-card")
            count = cards.count()
            print(f"ニュースカード数: {count}")
            
            if count > 0:
                print("[OK] ニュースが表示されています。")
                # エラーメッセージ（フォールバック）の確認
                first_card = cards.first
                summary = first_card.locator(".summary-box p").text_content()
                print(f"最初のニュースの要約: {summary}")
                
                if "要約機能は停止しています" in summary:
                    print("[OK] フォールバックメッセージが表示されています。")
            else:
                print("[WARN] ニュースカードが0件です（API制限またはデータなし）。")

            browser.close()
            
    finally:
        print("サーバーを停止しています...")
        server_process.terminate()
        server_process.wait()

if __name__ == "__main__":
    verify_browser()
