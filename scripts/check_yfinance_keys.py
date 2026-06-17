import yfinance as yf
import json


def check_info(symbol):
    t = yf.Ticker(symbol)
    info = t.info
    # keys of interest
    keys = [
        "dividendYield",
        "totalAssets",
        "totalStockholderEquity",
        "bookValue",
        "debtToEquity",
        "equity_ratio",
        "totalDebt",
        "marketCap",
        "priceToBook",
        "sharesOutstanding",
    ]
    res = {k: info.get(k) for k in keys}
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    check_info("8306.T")
