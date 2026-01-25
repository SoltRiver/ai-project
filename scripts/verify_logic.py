import sys
import os

sys.path.append(os.getcwd())
from services import stock_service

def verify_logic():
    print("Testing Search Logic (Prefix + Sort)...")
    
    # 1. Test Prefix: "72" should match 7203 (Toyota) but check others
    # Since I don't know what's in J-Quants exactly (it's down), check fallback logic mainly or mocked if I could.
    # But J-Quants is down, so it WILL use fallback map.
    # Fallback map has 7203, 7201, 7267.
    
    query = "72"
    results = stock_service.search_stocks(query)
    print(f"Query '{query}' Results: {[r['code'] for r in results]}")
    
    # Check Sort Order
    codes = [r['code'] for r in results]
    if codes == sorted(codes):
        print("PASS: Results are sorted ascending.")
    else:
        print("FAIL: Results are NOT sorted ascending.")
        
    # Check Prefix Constraint
    # Search "oyota" should NOT match "Toyota" (Name) if it only does prefix.
    # Actually wait, "Toyota" in map is "トヨタ自動車". "oyota" doesn't match that anyway.
    # Input "トヨタ" should match.
    # Input "ヨタ" should NOT match if prefix only.
    
    query_suffix = "ヨタ"
    results_suffix = stock_service.search_stocks(query_suffix)
    print(f"Query '{query_suffix}' Results: {[r['name'] for r in results_suffix]}")
    if not results_suffix:
        print("PASS: Suffix query 'ヨタ' returned no results (Strict Prefix).")
    else:
        print("FAIL: Suffix query returned results.")

    # 2. Test "gen" -> "9166" (GENDA)
    # Map now has "9166": "GENDA". "gen" matches "GENDA" prefix?
    query_gen = "gen"
    results_gen = stock_service.search_stocks(query_gen)
    print(f"Query '{query_gen}' Results: {results_gen}")
    
    has_genda = any(r['code'] == '9166' for r in results_gen)
    if has_genda:
        print("PASS: 'gen' matched GENDA (9166).")
    else:
        print("FAIL: 'gen' did NOT match GENDA.")
    
if __name__ == "__main__":
    verify_logic()
