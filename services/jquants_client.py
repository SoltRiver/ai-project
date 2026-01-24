import os
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dotenv import load_dotenv

# Load env vars from .env file if present
load_dotenv()

class JQuantsClient:
    BASE_URL = "https://api.jquants.com/v1"
    
    def __init__(self):
        self.refresh_token = os.environ.get("JQUANTS_REFRESH_TOKEN")
        self.id_token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None
        self._listed_issues_cache: List[Dict[str, Any]] = []

    def _get_id_token(self) -> str:
        """
        Get a valid ID token. Refreshes if expired or missing.
        """
        # Return existing if valid (with 1 min buffer)
        if self.id_token and self.token_expiry and datetime.now() < self.token_expiry - timedelta(minutes=1):
            return self.id_token

        if not self.refresh_token:
            print("WARN: JQUANTS_REFRESH_TOKEN not found in environment.")
            return ""

        try:
            url = f"{self.BASE_URL}/token/auth_user"
            resp = requests.post(url, params={"refresh_token": self.refresh_token})
            resp.raise_for_status()
            data = resp.json()
            self.id_token = data.get("idToken")
            # Usually lasts 24 hours, but safe default usually provided? API doesn't specify expiry in response body always,
            # but usually it's correct to just refresh when needed. Docs say 24h.
            self.token_expiry = datetime.now() + timedelta(hours=23) 
            return self.id_token
        except Exception as e:
            print(f"Error refreshing J-Quants token: {e}")
            return ""

    def get_listed_issues(self) -> List[Dict[str, Any]]:
        """
        Fetch list of listed issues (stocks). Use cache if populated.
        """
        if self._listed_issues_cache:
            return self._listed_issues_cache
            
        token = self._get_id_token()
        if not token:
            return []

        try:
            url = f"{self.BASE_URL}/listed/info"
            headers = {"Authorization": f"Bearer {token}"}
            resp = requests.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            
            # Response format: {"info": [...]}
            issues = data.get("info", [])
            self._listed_issues_cache = issues
            return issues
        except Exception as e:
            print(f"Error fetching J-Quants listed issues: {e}")
            return []

    def clear_cache(self):
        self._listed_issues_cache = []

# Global instance
client = JQuantsClient()
