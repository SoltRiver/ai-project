from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("http://127.0.0.1:8000/stocks/7203")
    time.sleep(2)

    html = page.evaluate("document.body.innerHTML")
    print("tab-content in HTML?", "tab-content" in html)
    print("candle-canvas in HTML?", "candle-canvas" in html)

    browser.close()
