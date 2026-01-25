import os
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dotenv import load_dotenv

# Load env vars from .env file if present
load_dotenv()

class JQuantsClient:
    BASE_URL = "https://api.jquants.com/v2"
    
    def __init__(self):
        # V2 uses API Key (x-api-key header)
        self.api_key = os.environ.get("JQUANTS_API_KEY")
        self._listed_issues_cache: List[Dict[str, Any]] = []

    def get_listed_issues(self) -> List[Dict[str, Any]]:
        """
        Fetch list of listed issues (stocks). Use cache if populated.
        V2 Endpoint: /v2/equities/master
        """
        if self._listed_issues_cache:
            return self._listed_issues_cache
            
        if not self.api_key:
            print("WARN: JQUANTS_API_KEY not found in environment.")
            return []

        try:
            url = f"{self.BASE_URL}/equities/master"
            headers = {"x-api-key": self.api_key}
            
            # Note: V2 might return specific columns or all. 
            # We just need simple list for now.
            resp = requests.get(url, headers=headers)
            resp.raise_for_status()
            
            # V2 Response format: { "data": [ ... ], "pagination_key": ... }
            body = resp.json()
            issues = body.get("data", [])
            
            # Check if column names are different. Assuming "Code" and "CompanyName" exist based on "master" naming.
            # If changed (e.g. "C", "N"), we might need mapping.
            # But "master" usually implies full info. Let's assume standard names or fallback to checking the first item in debug.
            
            self._listed_issues_cache = issues
            return issues
        except Exception as e:
            print(f"Error fetching J-Quants listed issues (v2): {e}")
            return []

    def clear_cache(self):
        self._listed_issues_cache = []

# Global instance
client = JQuantsClient()
