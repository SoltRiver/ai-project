from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("http://127.0.0.1:8000/stocks/7203")
    time.sleep(4)
    html = page.evaluate("document.body.innerHTML")
    with open("dom_after.html", "w", encoding="utf-8") as f:
        f.write(html)
    browser.close()
