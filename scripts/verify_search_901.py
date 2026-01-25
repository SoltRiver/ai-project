import sys
import os

sys.path.append(os.getcwd())
from services import stock_service

def verify_901():
    print("Testing Search for '901'...")
    query = "901"
    results = stock_service.search_stocks(query)
    
    codes = [r['code'] for r in results]
    print(f"Results for '901': {codes}")
    
    expected = ["9010", "9012", "9017"]
    missing = [e for e in expected if e not in codes]
    
    if not missing:
        print("PASS: Found expected 901x codes.")
    else:
        print(f"FAIL: Missing expected codes {missing}")

    # Check 904 (Kintetsu etc)
    print("Testing Search for '904'...")
    results_904 = stock_service.search_stocks("904")
    codes_904 = [r['code'] for r in results_904]
    print(f"Results for '904': {codes_904}")
    if "9041" in codes_904 and "9048" in codes_904:
        print("PASS: Found major private railways (904x).")

if __name__ == "__main__":
    verify_901()
