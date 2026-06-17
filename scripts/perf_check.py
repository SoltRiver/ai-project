import requests
import time

ENDPOINTS = [
    ("/glossary", "Static"),
    ("/candle-patterns", "Static"),
    ("/", "DB"),
    ("/calendar", "DB"),
    ("/indices", "External API"),
    ("/news", "External API"),
    ("/stocks/7203/tab/chart", "HTMX"),
    ("/stocks/7203/tab/fundamental", "HTMX"),
    ("/stocks/7203/tab/dividend", "HTMX"),
    ("/stocks/7203/tab/shareholder", "HTMX"),
    ("/partials/calendar/day?date=2026-05-15", "HTMX"),
    ("/partials/calendar/month_grid?year=2026&month=5", "HTMX"),
    ("/api/stocks/search?q=7203", "JSON API"),
]

BASE_URL = "http://127.0.0.1:8001"

print(f"{'Endpoint':<45} | {'Category':<15} | {'Status':<6} | {'Time (ms)'}")
print("-" * 80)

for path, category in ENDPOINTS:
    url = BASE_URL + path
    try:
        start = time.perf_counter()
        resp = requests.get(url, timeout=30)
        ms = (time.perf_counter() - start) * 1000
        print(f"{path:<45} | {category:<15} | {resp.status_code:<6} | {ms:.0f} ms")
    except Exception as e:
        print(f"{path:<45} | {category:<15} | ERROR  | {str(e)}")
