from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("http://127.0.0.1:8000/stocks/7203")
    time.sleep(2)

    # Check if #tab-content exists
    has_target = page.evaluate('!!document.querySelector("#tab-content")')
    print("Has #tab-content:", has_target)

    # Click tab 1
    buttons = page.locator('div[role="tablist"] button')
    if buttons.count() > 1:
        buttons.nth(1).click()
        time.sleep(2)
        has_target2 = page.evaluate('!!document.querySelector("#tab-content")')
        print("Has #tab-content after click:", has_target2)

    browser.close()
