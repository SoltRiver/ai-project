import os
import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REFRESH_TOKEN = "***REDACTED_JQUANTS_REFRESH_TOKEN***"
BASE_URL = "https://api.jquants.com/v1"

def test_refresh_token():
    url = f"{BASE_URL}/token/auth_refresh"
    print(f"Testing Refresh Token: {REFRESH_TOKEN}")
    
    try:
        resp = requests.post(url, params={"refreshtoken": REFRESH_TOKEN}, timeout=10)
        print(f"Status Code: {resp.status_code}")
        print(f"Response Body: {resp.text}")
        
        if resp.status_code == 200:
            print("SUCCESS: ID Token acquired.")
            data = resp.json()
            id_token = data.get("idToken")
            print(f"ID Token (first 20 chars): {id_token[:20]}...")
            return id_token
        else:
            print("FAILURE: Could not get ID token.")
            return None

    except Exception as e:
        print(f"Exception: {e}")
        return None

if __name__ == "__main__":
    test_refresh_token()
