
import os
import requests
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dotenv import load_dotenv

# Load env vars from .env file if present
load_dotenv()

logger = logging.getLogger(__name__)

class JQuantsClient:
    BASE_URL = "https://api.jquants.com/v1"
    
    def __init__(self):
        self.email = os.environ.get("JQUANTS_EMAIL")
        self.password = os.environ.get("JQUANTS_PASSWORD")
        self._refresh_token: Optional[str] = None
        self._id_token: Optional[str] = None
        self._id_token_expires_at: Optional[datetime] = None
        
        if not self.email or not self.password:
             logger.warning("JQUANTS_EMAIL or JQUANTS_PASSWORD not set. J-Quants features will be unavailable.")

    def _get_refresh_token(self) -> str:
        """
        Get refresh token using email/password.
        POST /token/auth_user
        """
        if self._refresh_token:
            return self._refresh_token
            
        url = f"{self.BASE_URL}/token/auth_user"
        payload = {"mailaddress": self.email, "password": self.password}
        
        try:
            resp = requests.post(url, json=payload, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            self._refresh_token = data.get("refreshToken")
            logger.info("J-Quants: Acquired Refresh Token")
            return self._refresh_token
        except Exception as e:
            logger.error(f"Failed to get J-Quants refresh token: {e}")
            raise

    def get_id_token(self) -> str:
        """
        Get ID token. Use cache if valid, else refresh.
        POST /token/auth_refresh
        """
        now = datetime.now()
        # Check cache (buffer 5 mins)
        if self._id_token and self._id_token_expires_at and now < self._id_token_expires_at:
            return self._id_token

        refresh_token = self._get_refresh_token()
        url = f"{self.BASE_URL}/token/auth_refresh"
        
        try:
            # Note: J-Quants v1 auth_refresh takes refreshtoken as query param
            resp = requests.post(url, params={"refreshtoken": refresh_token}, timeout=10)
            
            if resp.status_code == 401 or resp.status_code == 403:
                # Refresh token might be expired (it lasts 1 week usually), retry login once
                logger.warning("J-Quants refresh token expired or invalid. Re-authenticating...")
                self._refresh_token = None
                refresh_token = self._get_refresh_token()
                resp = requests.post(url, params={"refreshtoken": refresh_token}, timeout=10)

            resp.raise_for_status()
            data = resp.json()
            self._id_token = data.get("idToken")
            
            # ID Token usually lasts 24h. Set expiry.
            # We don't parse JWT here to keep it simple, just assume 23 hours to be safe.
            self._id_token_expires_at = now + timedelta(hours=23)
            logger.info("J-Quants: Acquired ID Token")
            return self._id_token
            
        except Exception as e:
            # If we fail, clear refresh token to force re-login next time
            self._refresh_token = None 
            logger.error(f"Failed to get J-Quants ID token: {e}")
            raise

    def get(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Authenticated GET request.
        """
        try:
            token = self.get_id_token()
        except:
            return {} # Return empty on auth failure to avoid crashing app
            
        url = f"{self.BASE_URL}{endpoint}"
        headers = {"Authorization": f"Bearer {token}"}
        
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=20)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"J-Quants API Request Failed ({endpoint}): {e}")
            return {}

    def get_daily_quotes(self, code: str, date: str = None, from_date: str = None, to_date: str = None) -> Dict[str, Any]:
        """
        /prices/daily_quotes
        """
        params = {"code": code}
        if date:
            params["date"] = date.replace("-", "") # J-Quants uses YYYYMMDD
        if from_date:
            params["from"] = from_date.replace("-", "")
        if to_date:
            params["to"] = to_date.replace("-", "")
            
        return self.get("/prices/daily_quotes", params)

    def get_listed_info(self, code: str) -> Dict[str, Any]:
        """
        /listed/info
        """
        # User note: prioritizes /listed/info for shares outstanding
        params = {"code": code}
        return self.get("/listed/info", params)
    def get_listed_issues(self) -> List[Dict[str, Any]]:
        """
        Get listed issues list from /listed/info
        """
        resp = self.get_listed_info("")
        return resp.get("info", [])

# Global instance
client = JQuantsClient()
