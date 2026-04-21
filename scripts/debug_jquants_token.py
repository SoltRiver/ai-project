import os
import requests
import logging

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 環境変数からリフレッシュトークンを取得（ハードコード禁止）
REFRESH_TOKEN = os.environ.get("JQUANTS_REFRESH_TOKEN")
BASE_URL = "https://api.jquants.com/v1"

def test_refresh_token():
    if not REFRESH_TOKEN:
        print("ERROR: JQUANTS_REFRESH_TOKEN が設定されていません。")
        print("  .env ファイルに JQUANTS_REFRESH_TOKEN=xxxxx を設定してください。")
        return None

    url = f"{BASE_URL}/token/auth_refresh"
    # トークンをマスクして表示（先頭4文字のみ）
    print(f"Testing Refresh Token: {REFRESH_TOKEN[:4]}{'*' * (len(REFRESH_TOKEN) - 4)}")
    
    try:
        resp = requests.post(url, params={"refreshtoken": REFRESH_TOKEN}, timeout=10)
        print(f"Status Code: {resp.status_code}")
        # レスポンスボディにトークンが含まれる可能性があるため、ステータスのみ表示
        print(f"Response Length: {len(resp.text)} chars")
        
        if resp.status_code == 200:
            print("SUCCESS: ID Token acquired.")
            data = resp.json()
            id_token = data.get("idToken")
            # IDトークンもマスクして表示
            print(f"ID Token (first 10 chars): {id_token[:10]}..." if id_token else "ID Token: -")
            return id_token
        else:
            print("FAILURE: Could not get ID token.")
            return None

    except Exception as e:
        print(f"Exception: {e}")
        return None

if __name__ == "__main__":
    test_refresh_token()
