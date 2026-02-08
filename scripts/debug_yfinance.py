
import yfinance as yf
import sys

def debug_yfinance(ticker="7203.T"):
    print(f"Fetching info for {ticker}...")
    t = yf.Ticker(ticker)
    info = t.info
    
    print("\n--- Key Financials in Info ---")
    keys = [
        "totalRevenue", "revenuePerShare",
        "netIncomeToCommon", "trailingEps",
        "totalAssets", "totalStockholderEquity",
        "operatingCashflow", "freeCashflow",
        "operatingMargins", "profitMargins",
        "returnOnAssets", "returnOnEquity",
        "ebitda", "grossProfits",
        "bookValue", "sharesOutstanding",
        "debtToEquity", "currentRatio"
    ]
    
    for k in keys:
        print(f"{k}: {info.get(k)}")

    print("\n--- All Keys ---")
    # print(info.keys()) # Uncomment to see all

if __name__ == "__main__":
    debug_yfinance()
