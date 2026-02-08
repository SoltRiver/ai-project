import sys
import os
import requests
import time
import sqlite3

BASE_URL = "http://localhost:8000"
DB_PATH = "ai_project.db"

def test_persistence():
    print("Testing persistence...")
    
    # Wait for server
    print("Waiting for server...")
    try:
        requests.get(f"{BASE_URL}/stocks")
    except:
        print("Server not ready. Please start server.")
        return

    # 1. List current stocks
    print("1. Listing stocks...")
    try:
        r = requests.get(f"{BASE_URL}/stocks")
        # Check defaults are there (e.g. 7203)
        if "7203" in r.text or "トヨタ" in r.text:
            print("   CHECK OK: Default stock found.")
        else:
            print("   WARNING: Default stock NOT found.")
    except Exception as e:
        print(f"   Failed to list stocks: {e}")
        return

    # 2. Add new stock (e.g. 9101 - NYK)
    print("2. Adding stock 9101...")
    try:
        payload = {"code": "9101"}
        r = requests.post(f"{BASE_URL}/stocks/add", data=payload, allow_redirects=True)
        if r.status_code == 200 and ("9101" in r.text or "日本郵船" in r.text):
            print("   CHECK OK: Stock 9101 added successfully.")
        else:
            print(f"   Failed to add stock 9101. Status: {r.status_code}")
    except Exception as e:
        print(f"   Exception adding stock: {e}")

    # 3. Verify DB content via SQLite directly
    print("3. Verifying DB content direct access...")
    if not os.path.exists(DB_PATH):
        print(f"   ERROR: DB file {DB_PATH} not found.")
    else:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT code FROM stocks WHERE code='9101'")
            row = cursor.fetchone()
            if row:
                print("   CHECK OK: Stock 9101 found in SQLite DB.")
            else:
                print("   ERROR: Stock 9101 NOT found in SQLite DB.")
            conn.close()
        except Exception as e:
            print(f"   DB check failed: {e}")

    # 4. Remove stock
    print("4. Removing stock 9101...")
    try:
        payload = {"selected_stocks": ["9101"]}
        r = requests.post(f"{BASE_URL}/stocks/delete", data=payload, allow_redirects=True)
        if "9101" not in r.text:
             print("   CHECK OK: Stock 9101 removed successfully.")
        else:
             print("   WARNING: Stock 9101 still present after delete (or list verify failed).")
    except Exception as e:
        print(f"   Exception removing stock: {e}")

if __name__ == "__main__":
    test_persistence()
