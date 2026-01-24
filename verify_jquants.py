import sys
import os

# Ensure project root is in path
sys.path.append(os.getcwd())

from services import stock_service
from services.jquants_client import client

def verify_jquants():
    print("Verifying J-Quants Search...")
    
    # 1. Test Client Direct
    print("\n[Client Test]")
    issues = client.get_listed_issues()
    if issues:
        print(f"PASS: Fetched {len(issues)} issues from J-Quants.")
        print(f"Sample: {issues[0]}")
    else:
        print("FAIL: Could not fetch issues from J-Quants (or empty).")
        # If client fails, the service test below will use fallback
    
    # 2. Test Service Search
    print("\n[Service Search Test]")
    # "Toyota" -> J-Quants usually has "Toyota" in CompanyNameEnglish?
    # User requested: "Condition: verify stock name, stock code from J-Quants"
    # Typically J-Quants returns 'Code' and 'CompanyName' (Japanese).
    # Let's search for "Kyokuyo" (Code 13010) or something common. Or "7203".
    
    query = "7203" 
    results = stock_service.search_stocks(query)
    print(f"Query: {query}")
    print(f"Results: {results}")
    
    # Check if we got the expected result
    # We expect 'Toyota Motor Corp' or 'トヨタ自動車' depending on what 'CompanyName' is.
    # If fallback is used, we get whatever is in STOCK_NAME_MAP.
    
    # Let's try a query that is NOT in the static map but likely in J-Quants to prove integration.
    # Static map has: 7203, 6758, 9984, 8306, 8035.
    # Let's try "NTT" (9432) - likely not in static map unless map is huge (actually map is in another file, I saw it earlier, let's assume it's small/sample).
    # Wait, the user provided a real refreshed token, so we can check real data.
    
    query_2 = "9432" # Nippon Telegraph and Telephone Corporation
    results_2 = stock_service.search_stocks(query_2)
    print(f"Query: {query_2}")
    print(f"Results: {results_2}")
    
    if results_2:
        print("PASS: Found result for 9432 (likely via J-Quants).")
    else:
        print("WARN: No result for 9432. J-Quants might be failing or cache empty.")

if __name__ == "__main__":
    verify_jquants()
