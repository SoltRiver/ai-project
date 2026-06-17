from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()

    # Catch console errors and network requests
    page.on("console", lambda msg: print("CONSOLE:", msg.text))
    page.on("response", lambda res: print("RESPONSE:", res.url, res.status))

    page.goto("http://127.0.0.1:8000/stocks/7203")
    time.sleep(2)
    browser.close()
