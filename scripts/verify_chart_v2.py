
import sys
import os
import logging
import json

# Add project root to sys.path
sys.path.append(os.getcwd())

# Configure logging to stdout
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from services.jquants_client import client

def verify_chart():
    print("--- Verifying Chart Data (Daily Quotes) V2 ---")
    
    # Try fetching data for Toyota (7203) for a known valid date
    # Using 2024-01-04 as single date
    print("Fetching single date (2024-01-04)...")
    try:
        data = client.get_daily_quotes(code="7203", date="2024-01-04")
        if data and "daily_quotes" in data:
            quotes = data["daily_quotes"]
            print(f"Success! Count: {len(quotes)}")
            if len(quotes) > 0:
                print(f"Sample Quote: {quotes[0]}")
                # Check keys
                keys = quotes[0].keys()
                required = ["Date", "Open", "High", "Low", "Close", "Volume"]
                if all(k in keys for k in required):
                    print("[PASS] All required keys present.")
                else:
                    print(f"[FAIL] Missing keys. Found: {list(keys)}")
        else:
            print("[FAIL] No data returned or empty 'daily_quotes'")
            print(f"Raw Response: {data}")

    except Exception as e:
        print(f"[ERROR] {e}")

    print("\nFetching range (2024-01-04 to 2024-01-10)...")
    try:
        data = client.get_daily_quotes(code="7203", from_date="2024-01-04", to_date="2024-01-10")
        if data and "daily_quotes" in data:
            quotes = data["daily_quotes"]
            print(f"Success! Count: {len(quotes)}")
            # Expected roughly 4-5 trading days
        else:
            print("[FAIL] Range fetch failed.")

    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    verify_chart()
