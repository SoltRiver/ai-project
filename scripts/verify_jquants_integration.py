
import requests
import json
import time

BASE_URL = "http://localhost:8000"
DOC_ID = "S100TK3X" # Godo Steel (Likely available from previous tests)

def verify_jquants():
    print(f"--- Verifying J-Quants Integration for {DOC_ID} ---")
    
    # 1. Ensure Document is Downloaded
    print(f"[1] Ensuring document {DOC_ID} is available...")
    try:
        url = f"{BASE_URL}/api/edinet/documents/{DOC_ID}/download"
        print(f"Calling: {url}")
        resp = requests.get(url, timeout=30)
        if resp.status_code != 200:
            print(f"Failed to download/prepare document: {resp.status_code} {resp.text}")
            return
        print("Document ready.")
    except Exception as e:
        print(f"Error calling download API: {e}")
        # If server not running?
        return

    # 2. Get Fundamentals WITH market
    print(f"[2] Fetching Fundamentals with Market Data (with_market=true)...")
    url = f"{BASE_URL}/api/fundamentals/edinet/{DOC_ID}?with_market=true"
    start = time.time()
    resp = requests.get(url, timeout=30)
    elapsed = time.time() - start
    
    if resp.status_code != 200:
        print(f"Check failed: Status {resp.status_code} {resp.text}")
        return
        
    data = resp.json()
    print(f"Response Received in {elapsed:.2f}s")
    
    # 3. Validation
    # Check Financials
    fin = data.get("financials", {})
    sec_code = fin.get("sec_code")
    print(f"Financials Extracted. SecCode: {sec_code}")
    
    # Check Market
    market = data.get("market")
    if market:
        print("Market Data Retrieved:")
        print(json.dumps(market, indent=2, ensure_ascii=False))
        if market.get("price"):
            print(" PASS: Price found.")
        else:
            print(" WARN: Price is null (Holiday? or J-Quants Data missing?)")
    else:
        print(" WARN: Market Data is None. (J-Quants Auth failed or API error?)")
        print(json.dumps(data.get("meta"), indent=2, ensure_ascii=False))

    # Check Ratios
    ratios = data.get("ratios")
    if ratios:
        print("Ratios Calculated:")
        print(json.dumps(ratios, indent=2, ensure_ascii=False))
        if ratios.get("per") or ratios.get("pbr"):
            print(" PASS: PER/PBR calculated.")
    else:
        print(" WARN: Ratios is None.")

    print("--- Verification Complete ---")

if __name__ == "__main__":
    verify_jquants()
