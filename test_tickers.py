
import yfinance as yf

tickers = {
    "Nikkei 225": "^N225",
    "TOPIX": "0000.st", # Often used for TOPIX, or maybe try others
    "TOPIX_alt": "^TOPX", 
    "Nikkei Futures": "NIY=F", # CME
    "Nikkei Futures OSE": "NK=F", # OSE
    "JASDAQ": "^DJJAS",
    "JASDAQ_alt": "^NOTHER", # ?
    "NY Dow": "^DJI",
    "NASDAQ": "^IXIC",
    "Mothers": "^MOTHERS", # ?
    "Growth": "^TG15" # ?
}

print("Testing Tickers...")
for name, symbol in tickers.items():
    try:
        t = yf.Ticker(symbol)
        hist = t.history(period="1d")
        if not hist.empty:
            print(f"[OK] {name} ({symbol}): {hist['Close'].iloc[-1]}")
        else:
            print(f"[FAIL] {name} ({symbol}): No history")
    except Exception as e:
        print(f"[ERROR] {name} ({symbol}): {e}")
