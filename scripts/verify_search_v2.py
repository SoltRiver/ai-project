import sys
import os
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.getcwd())
try:
    from services.jquants_client import client
    from services import stock_service
except ImportError:
    pass

def verify_search_v2():
    print("--- Verifying Search with J-Quants V2 ---")
    
    # 1. Ensure client can fetch
    issues = client.get_listed_issues()
    if not issues:
        print("FAIL: Client returned empty list. Check API Key.")
        return

    print(f"Client fetched {len(issues)} issues.")
    
    # 2. Test Search via Service
    # Toyota (7203) should be there.
    query = "7203"
    print(f"Searching for '{query}'...")
    results = stock_service.search_stocks(query)
    
    print(f"Found {len(results)} results.")
    print(f"Top result: {results[0] if results else 'None'}")
    
    # Check if name is populated (means CoName mapping worked)
    if results and results[0]['name']:
        print(f"PASS: Name '{results[0]['name']}' found. V2 mapping works.")
    else:
        print("FAIL: Name is empty. Check mapping.")

    # 3. Test English Name search (if available)
    # Search "Toyota"
    query_en = "Toyota"
    print(f"Searching for English '{query_en}'...")
    results_en = stock_service.search_stocks(query_en)
    
    if any(r['code'] == '7203' for r in results_en):
        print("PASS: Found Toyota by English name.")
    else:
         print("WARN: Toyota not found by English name (maybe data missing in J-Quants or logic issue).")

if __name__ == "__main__":
    verify_search_v2()
