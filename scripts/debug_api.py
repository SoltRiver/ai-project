
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def debug_api():
    api_key = os.getenv("EDINET_API_KEY")
    # APIキーはマスクして表示（先頭4文字のみ）
    print(f"API Key: {api_key[:4]}{'*' * 8}" if api_key else "API Key: -")
    
    url = "https://api.edinet-fsa.go.jp/api/v2/documents.json"
    params = {
        "date": "2024-06-26",
        "type": 1, # 1: Metadata, 2: List
        "Subscription-Key": api_key
    }
    
    # パラメータ出力時はAPIキーをマスク
    safe_params = {k: (v[:4] + '****' if k == 'Subscription-Key' and v else v) for k, v in params.items()}
    print(f"Requesting: {url} with params {safe_params}")
    try:
        res = requests.get(url, params=params)
        print(f"Status: {res.status_code}")
        print(f"Headers: {res.headers}")
        print(f"Content: {res.text[:1000]}") # Print first 1000 chars
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_api()
