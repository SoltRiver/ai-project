
import requests
import json
import logging
import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# User provided key
API_KEY = "***REDACTED_JQUANTS_API_KEY***"
BASE_URL = "https://api.jquants.com/v2"

def verify_v2_access():
    headers = {"x-api-key": API_KEY}
    
    # 1. Verify /equities/master (Listed Issues)
    # Note: V2 might require 'date' or 'code'. Trying with date.
    print("--- Verifying /equities/master ---")
    url = f"{BASE_URL}/equities/master"
    # Try yesterday (2026-02-10)
    # If today is 2026-02-11, yesterday was Tue.
    params = {"date": "20260210"} 
    
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            # Expecting a list or a dict with a list
            # V2 often returns direct list for CSV-like data, or JSON objects?
            # Search execution said it returns pandas DataFrame in Python client, but raw API returns JSON.
            # Let's inspect the type.
            if isinstance(data, dict):
                 print(f"Response Keys: {list(data.keys())}")
                 # Check if 'data' key exists? Wait, the output said Response Keys: ['data']?
                 # No, requests .json() returns the dict. The keys of that dict are ['data']?
                 # Wait, my previous code printed: Response Keys: ['data']
                 # So yes, the dict has a key "data".
                 
                 if "data" in data:
                     inner = data["data"]
                     print(f"Inner Data Type: {type(inner)}")
                     if isinstance(inner, list):
                         print(f"Inner List Count: {len(inner)}")
                         if len(inner) > 0:
                             print(f"Sample Item: {inner[0]}")
                     elif isinstance(inner, dict):
                         print(f"Inner Dict Keys: {list(inner.keys())}")
                         # Maybe equities is here?
                 else:
                     print("No 'data' key found, but keys are:", list(data.keys()))
        else:
            print(f"Error Body: {resp.text}")

    except Exception as e:
        print(f"Exception: {e}")

    # 2. Verify /equities/bars/daily (Daily Quotes)
    print("\n--- Verifying /equities/bars/daily ---")
    url = f"{BASE_URL}/equities/bars/daily"
    params = {"code": "7203", "date": "20240104"} 
    
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict):
                print(f"Response Keys: {list(data.keys())}")
                if "data" in data:
                    inner = data["data"]
                    if isinstance(inner, list) and len(inner) > 0:
                         print(f"Sample Quote Keys: {list(inner[0].keys())}")
                    elif isinstance(inner, dict):
                         # Maybe daily_quotes is inside?
                         if "daily_quotes" in inner:
                             print(f"Sample Quote Keys: {list(inner['daily_quotes'][0].keys())}")
                         else:
                             print(f"Inner Dict Keys: {list(inner.keys())}")


    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    verify_v2_access()
