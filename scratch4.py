import urllib.request

with urllib.request.urlopen("http://127.0.0.1:8000/stocks/7203/tab/chart") as res:
    html = res.read().decode("utf-8")
    print("candle-canvas in response?", "candle-canvas" in html)
    print("HTML length:", len(html))
    print("First 100 chars:", html[:100])
