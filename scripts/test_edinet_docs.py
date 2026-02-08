
import requests
import json
import os
import sys

# Test Localhost API
BASE_URL = "http://localhost:8000/api/edinet/documents"
DOC_ID = "S100TK3X" # Godo Steel

def test_docs_specific():
    print(f"=== Testing EDINET Document Processing for {DOC_ID} (Retry) ===")
    
    # 2. Call Download API
    print(f"\n[Step 1] Downloading ZIP for {DOC_ID}...")
    try:
        # Force false to use existing if valid
        res = requests.get(f"{BASE_URL}/{DOC_ID}/download", params={"force": "false"}, timeout=60)
        print(f"Status: {res.status_code}")
        if res.status_code == 200:
            result = res.json()
            print("SUCCESS: Download & Extraction complete.")
            print(f"Saved ZIP: {result.get('saved_zip')}")
            print(f"Unzipped: {result.get('unzipped_dir')}")
            print(f"Primary XBRL: {result.get('primary_xbrl')}")
            print(f"Inline XBRL Files: {len(result.get('inline_xbrl_files', []))}")
            if result.get('inline_xbrl_files'):
                print(f" - First: {result.get('inline_xbrl_files')[0]}")
        else:
            print(f"FAIL: Download failed. {res.text[:200]}")
            return
    except Exception as e:
        print(f"ERROR: Download exception - {e}")
        return

    # 3. Call Financials API
    print(f"\n[Step 2] Extracting Financials for {DOC_ID}...")
    try:
        res = requests.get(f"{BASE_URL}/{DOC_ID}/financials", timeout=30)
        print(f"Status: {res.status_code}")
        if res.status_code == 200:
            result = res.json()
            fin = result.get("financials", {})
            print("SUCCESS: Financials extracted (or graceful fallback).")
            print(json.dumps(fin, indent=2, ensure_ascii=False))
        else:
            print(f"FAIL: Extraction failed. {res.text[:500]}")
    except Exception as e:
        print(f"ERROR: Extraction exception - {e}")

if __name__ == "__main__":
    test_docs_specific()
