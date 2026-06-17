from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()

    # We will log the DOM mutation of #tab-content
    page.goto("http://127.0.0.1:8000/stocks/7203")

    # Immediately check
    print("Initial check:", page.evaluate('!!document.querySelector("#tab-content")'))

    # Wait for HTMX
    time.sleep(3)

    # Check again
    print("After 3s check:", page.evaluate('!!document.querySelector("#tab-content")'))

    browser.close()
