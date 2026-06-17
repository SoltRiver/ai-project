import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd

RANKING_UNIVERSE = [
    "7203.T",
    "6758.T",
    "9984.T",
    "8306.T",
    "8035.T",
    "6098.T",
    "4063.T",
    "6861.T",
    "4502.T",
    "8316.T",
    "9432.T",
    "9433.T",
    "6501.T",
    "6954.T",
    "7741.T",
    "4519.T",
    "7974.T",
    "8001.T",
    "8031.T",
    "6367.T",
]


def debug_fetch():
    needed_days = 7
    start_date = (datetime.now() - timedelta(days=needed_days)).strftime("%Y-%m-%d")
    print(f"Fetching from {start_date}...")

    data = yf.download(
        RANKING_UNIVERSE,
        start=start_date,
        interval="1d",
        group_by="ticker",
        threads=True,
    )
    if data.empty:
        print("Data is empty!")
        return

    results = []
    for ticker in RANKING_UNIVERSE:
        if ticker not in data.columns.levels[0]:
            continue

        df = data[ticker].dropna()
        if len(df) < 2:
            print(f"Ticker {ticker} has less than 2 rows of data.")
            continue

        current_price = float(df["Close"].iloc[-1])
        base_price = float(df["Close"].iloc[-2])

        change = current_price - base_price
        change_percent = (change / base_price) * 100

        results.append({"ticker": ticker, "change_percent": change_percent})

    print(f"Total results: {len(results)}")
    top = sorted(results, key=lambda x: x["change_percent"], reverse=True)[:10]
    bottom = sorted(results, key=lambda x: x["change_percent"])[:10]

    print("\nTOP 5:")
    for item in top[:5]:
        print(f"{item['ticker']}: {item['change_percent']:.2f}%")

    print("\nBOTTOM 5:")
    for item in bottom[:5]:
        print(f"{item['ticker']}: {item['change_percent']:.2f}%")


if __name__ == "__main__":
    debug_fetch()
