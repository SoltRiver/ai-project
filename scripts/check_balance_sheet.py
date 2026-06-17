import yfinance as yf


def check_bs(symbol):
    t = yf.Ticker(symbol)
    bs = t.balance_sheet
    print("Balance Sheet Index (Keys):")
    print(bs.index.tolist())

    # Try to find Total Assets
    if "Total Assets" in bs.index:
        print(f"Total Assets: {bs.loc['Total Assets'].iloc[0]}")
    elif "TotalAssets" in bs.index:
        print(f"Total Assets: {bs.loc['TotalAssets'].iloc[0]}")
    else:
        print("Total Assets not found in index.")

    if "Stockholders Equity" in bs.index:
        print(f"Stockholders Equity: {bs.loc['Stockholders Equity'].iloc[0]}")
    elif "Total Stockholder Equity" in bs.index:
        print(f"Stockholders Equity: {bs.loc['Total Stockholder Equity'].iloc[0]}")


if __name__ == "__main__":
    check_bs("8306.T")
