import sys
import os

sys.path.append(os.getcwd())
from services import stock_service

def verify_fallback():
    print("Testing Search Fallback for GENDA (9166)...")
    results = stock_service.search_stocks("9166")
    print(f"Results for '9166': {results}")
    
    found = any(r['code'] == '9166' for r in results)
    if found:
        print("PASS: GENDA found in search results.")
    else:
        print("FAIL: GENDA not found.")

    results_name = stock_service.search_stocks("GENDA")
    print(f"Results for 'GENDA': {results_name}")
    if any(r['code'] == '9166' for r in results_name):
         print("PASS: GENDA found by name.")
    
if __name__ == "__main__":
    verify_fallback()
