import requests
import sys

BASE_URL = "http://localhost:8000"

def check_url(url, description):
    print(f"Checking {description} ({url})...", end=" ")
    try:
        resp = requests.get(url)
        if resp.status_code == 200:
            print("OK")
            return True
        else:
            print(f"FAIL (Status {resp.status_code})")
            return False
    except Exception as e:
        print(f"FAIL (Error: {e})")
        return False

def regression_test():
    print("\n--- Regression Testing ---")
    all_pass = True
    
    # Check key pages
    pages = [
        ("/", "Home/Stock List"),
        ("/stocks", "Stock List (Explicit)"),
        ("/glossary", "Glossary"),
        ("/candle-patterns", "Candle Patterns"),
    ]
    
    for url, desc in pages:
        if not check_url(f"{BASE_URL}{url}", desc):
            all_pass = False

    # Check detail page of a known stock (assuming 7203 Toyota is usually there or added)
    # If not present, we should add it first or check list to find one.
    print("Fetching stock list to find a valid code...")
    try:
        resp = requests.get(f"{BASE_URL}/stocks")
        if resp.status_code == 200:
            html = resp.text
            # Simple parsing to find a link like /stocks/XXXX
            import re
            match = re.search(r'/stocks/(\d{4})', html)
            if match:
                code = match.group(1)
                print(f"Found stock code {code} in list. Checking detail tabs...")
                
                tabs = ["", "/tab/chart", "/tab/fundamental", "/tab/dividend", "/tab/shareholder"]
                for tab in tabs:
                    url = f"{BASE_URL}/stocks/{code}{tab}"
                    if not check_url(url, f"Detail {code} Tab{tab}"):
                        all_pass = False
            else:
                print("WARNING: No stocks found in list. Skipping detail regression.")
        else:
            print("FAIL: Could not fetch stock list.")
            all_pass = False
    except Exception as e:
        print(f"Error during list fetch: {e}")
        all_pass = False

    return all_pass

if __name__ == "__main__":
    success = regression_test()
    if success:
        print("\nRegression Test: PASS")
        sys.exit(0)
    else:
        print("\nRegression Test: FAIL")
        sys.exit(1)
