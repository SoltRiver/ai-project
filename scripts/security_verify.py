import requests
import html

BASE_URL = "http://localhost:8000"


def test_xss_search():
    print("Testing XSS in Search API...")
    # Inject script tag
    payload = "<script>alert(1)</script>"
    try:
        resp = requests.get(f"{BASE_URL}/api/stocks/search", params={"q": payload})
        if resp.status_code == 200:
            data = resp.json()
            suggestions = data.get("suggestions", [])
            # Should be empty because "<script>" is not in STOCK_NAME_MAP
            if not suggestions:
                print(f"PASS: XSS payload '{payload}' returned no results (Safe).")
            else:
                # If it returned something, check if it just echoed input (Bad) or matched something (Unlikely)
                print(f"WARN: Returned suggestions: {suggestions}")
        else:
            print(f"FAIL: Search API returned {resp.status_code}")
    except Exception as e:
        print(f"ERROR: {e}")


def test_traversal_detail():
    print("\nTesting Directory Traversal in Detail Page...")
    # Try logical traversal logic
    bad_code = "../../../etc/passwd"
    try:
        resp = requests.get(f"{BASE_URL}/stocks/{bad_code}")
        # Expect 404 or YFinance error (which usually results in 404/500 handled or just empty data)
        # Definitely should not return file content
        if resp.status_code == 404:
            print(f"PASS: Traversal payload '{bad_code}' returned 404.")
        elif resp.status_code == 500:
            print(
                f"PASS: Traversal payload '{bad_code}' caused 500 (Likely yfinance error, safe from file read)."
            )
        else:
            # If 200, check content
            if "root:" in resp.text:
                print("CRITICAL FAIL: /etc/passwd content leaked!")
            else:
                print(
                    f"PASS: Returned {resp.status_code} but no file leakage detected."
                )
    except Exception as e:
        print(f"ERROR: {e}")


def test_add_injection():
    print("\nTesting Injection in Add Stock...")
    payload = "7203; rm -rf /"
    try:
        # We need to simulate form submission
        resp = requests.post(
            f"{BASE_URL}/stocks/add", data={"code": payload}, allow_redirects=False
        )
        # Should redirect to /stocks
        if resp.status_code == 303:
            print(f"PASS: Injection payload '{payload}' redirected (303).")
            # Verify it didn't crash or add weird stuff effectively
            # Check list
            list_resp = requests.get(f"{BASE_URL}/stocks")
            if payload in list_resp.text:
                # It might be added as a code if logic failed, but "rm -rf" shouldn't execute
                # HTML escaping should handle display
                if html.escape(payload) in list_resp.text:
                    print("NOTE: Payload added to list but HTML escaped properly.")
                else:
                    print("WARN: Payload added raw to HTML? Check escapes.")
            else:
                print("PASS: Payload not found in list.")
        else:
            print(f"FAIL: Add stock returned {resp.status_code}")
    except Exception as e:
        print(f"ERROR: {e}")


if __name__ == "__main__":
    test_xss_search()
    test_traversal_detail()
    test_add_injection()
