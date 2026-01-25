import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def test_search():
    print("Testing Search...")
    # Test English
    resp = requests.get(f"{BASE_URL}/api/stocks/search", params={"q": "Sony"})
    if resp.status_code == 200:
        data = resp.json()
        print(f"Search 'Sony': {data}")
        # Expect suggestions like "ソニーグループ (6758)"
        suggestions = data.get("suggestions", [])
        if any("6758" in s for s in suggestions):
            print("PASS: Found Sony")
        else:
            print("FAIL: Sony not found")
    else:
        print(f"FAIL: Search status {resp.status_code}")

    # Test Japanese
    resp = requests.get(f"{BASE_URL}/api/stocks/search", params={"q": "トヨタ"})
    if resp.status_code == 200:
        data = resp.json()
        print(f"Search 'トヨタ': {data}")
        if any("7203" in s for s in data.get("suggestions", [])):
            print("PASS: Found Toyota")
        else:
            print("FAIL: Toyota not found")
    else:
        print(f"FAIL: Search status {resp.status_code}")

def test_add():
    print("\nTesting Add...")
    
    # 1. Add by Name (Code) format - e.g. from Autocomplete
    # Using Keyence 6861
    payload = {"code": "キーエンス (6861)"}
    resp = requests.post(f"{BASE_URL}/stocks/add", data=payload)
    print(f"Add 'キーエンス (6861)': Status {resp.status_code}")
    
    # 2. Add by Name only - e.g. "任天堂" -> 7974
    payload2 = {"code": "任天堂"}
    resp2 = requests.post(f"{BASE_URL}/stocks/add", data=payload2)
    print(f"Add '任天堂': Status {resp2.status_code}")

    # 3. Add by Code only
    payload3 = {"code": "9983"} # Fast Retailing
    resp3 = requests.post(f"{BASE_URL}/stocks/add", data=payload3)
    print(f"Add '9983': Status {resp3.status_code}")

def test_list():
    print("\nVerifying List...")
    resp = requests.get(f"{BASE_URL}/stocks")
    if resp.status_code == 200:
        html = resp.text
        # Check if added stocks are present in HTML
        # 6861 Keyence
        if "6861" in html or "キーエンス" in html:
            print("PASS: Keyence found in list")
        else:
            print("FAIL: Keyence NOT found")
            
        # 7974 Nintendo
        if "7974" in html or "任天堂" in html:
            print("PASS: Nintendo found in list")
        else:
            print("FAIL: Nintendo NOT found")

        # 9983 Fast Retailing
        if "9983" in html:
            print("PASS: Fast Retailing found in list")
        else:
            print("FAIL: Fast Retailing NOT found")
    else:
        print(f"FAIL: List status {resp.status_code}")

if __name__ == "__main__":
    try:
        test_search()
        test_add()
        test_list()
    except Exception as e:
        print(f"Error: {e}")
