
import requests
import sys

BASE_URL = "http://localhost:8002"

def test_ui_search():
    print("--- Testing UI Search Endpoint ---")
    url = f"{BASE_URL}/api/edinet/documents/ui/search"
    try:
        resp = requests.get(url)
        if resp.status_code == 200:
            print("OK: /ui/search returned 200")
            if "EDINET 書類検索" in resp.text:
                 print("OK: Content contains 'EDINET 書類検索'")
            else:
                 print("WARN: Content missing expected title.")
        else:
            print(f"FAIL: /ui/search returned {resp.status_code}")
    except Exception as e:
        print(f"FAIL: Connection error: {e}")

def test_report_endpoint():
    print("\n--- Testing Report Endpoint ---")
    # Use the DocID from Plan D verification: S100TK3X
    doc_id = "S100TK3X"
    url = f"{BASE_URL}/api/fundamentals/reports/{doc_id}"
    try:
        resp = requests.get(url)
        if resp.status_code == 200:
            print(f"OK: /reports/{doc_id} returned 200")
            if "ファンダメンタル分析 (EDINET版)" in resp.text:
                print("OK: Content contains 'ファンダメンタル分析'")
            if "ROE" in resp.text:
                print("OK: Content contains 'ROE'")
        elif resp.status_code == 404:
             print("WARN: Document not found (need to download first?). Expected if server restarted and tmp cleared.")
             # Trigger download first to be sure
             print("Triggering download...")
             requests.get(f"{BASE_URL}/api/edinet/documents/{doc_id}/download")
             resp = requests.get(url)
             if resp.status_code == 200:
                 print("OK: Retry successful.")
             else:
                 print(f"FAIL: Retry returned {resp.status_code}")
        else:
            print(f"FAIL: /reports/{doc_id} returned {resp.status_code}")
            print(resp.text[:200])
    except Exception as e:
        print(f"FAIL: Connection error: {e}")

if __name__ == "__main__":
    test_ui_search()
    test_report_endpoint()
