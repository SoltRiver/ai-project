import os
import requests
from dotenv import load_dotenv

load_dotenv()

REFRESH_TOKEN = os.environ.get("JQUANTS_REFRESH_TOKEN")
BASE_URL = "https://api.jquants.com/v1"

def debug_auth():
    print("--- J-Quants Auth Debug ---")
    if not REFRESH_TOKEN:
        print("ERROR: JQUANTS_REFRESH_TOKEN is missing.")
        return

    url = f"{BASE_URL}/token/auth_user"
    print(f"Target URL: {url}")
    print("Attempting to get ID Token...")
    
    try:
        resp = requests.post(url, params={"refresh_token": REFRESH_TOKEN})
        print(f"Status Code: {resp.status_code}")
        print(f"Response Headers: {resp.headers}")
        print(f"Response Body: {resp.text[:500]}") # Truncate for safety/brevity
        
        if resp.status_code == 200:
            print("SUCCESS: Login (Token Refresh) successful.")
        else:
            print("FAILURE: Login failed.")
            
    except Exception as e:
        print(f"EXCEPTION: {e}")

if __name__ == "__main__":
    debug_auth()
