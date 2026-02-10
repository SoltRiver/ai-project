
import os
import requests
import logging
import time
from datetime import datetime, timedelta

from typing import Optional, Dict, List, Any
from dotenv import load_dotenv

# Load env vars from .env file if present
load_dotenv()

logger = logging.getLogger(__name__)

class JQuantsClient:
    BASE_URL = "https://api.jquants.com/v2"
    
    def __init__(self):
        self.api_key = os.environ.get("JQUANTS_API_KEY")
        
        if not self.api_key:
             logger.warning("JQUANTS_API_KEY not set. J-Quants features will be unavailable.")

    def get(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Authenticated GET request using x-api-key.
        """
        if not self.api_key:
            return {}
            
        url = f"{self.BASE_URL}{endpoint}"
        headers = {"x-api-key": self.api_key}
        
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=20)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"J-Quants API Request Failed ({endpoint}): {e}")
            return {}

    def get_daily_quotes(self, code: str, date: str = None, from_date: str = None, to_date: str = None) -> Dict[str, Any]:
        """
        /equities/bars/daily
        """
        params = {"code": code}
        if date:
            params["date"] = date.replace("-", "") # J-Quants uses YYYYMMDD
        if from_date:
            params["from"] = from_date.replace("-", "")
        if to_date:
            params["to"] = to_date.replace("-", "")
            
        resp = self.get("/equities/bars/daily", params)
        
        if "data" in resp:
            # Map keys O->Open, H->High, etc.
            standardized = []
            for item in resp["data"]:
                new_item = item.copy()
                mapping = {
                    "O": "Open", "H": "High", "L": "Low", "C": "Close", "Vo": "Volume",
                    "AdjO": "AdjOpen", "AdjH": "AdjHigh", "AdjL": "AdjLow", "AdjC": "AdjClose", "AdjVo": "AdjVolume"
                }
                for old_k, new_k in mapping.items():
                    if old_k in new_item:
                         new_item[new_k] = new_item.pop(old_k)
                standardized.append(new_item)
            
            resp["daily_quotes"] = standardized
            
        return resp

    def get_listed_issues(self) -> List[Dict[str, Any]]:
        """
        Get listed issues master.
        Strategy:
        1. Try today (Optimistic).
        2. If fails, try 13 weeks ago (Likely Free Plan).
        3. If fails, try last 7 days (Maybe just holiday/weekend for Premium).
        4. Deep fallback.
        """
        # 1. Try Today
        try:
            today = datetime.now().strftime("%Y%m%d")
            resp = self.get("/equities/master", {"date": today})
            if isinstance(resp, dict) and "data" in resp and resp["data"]:
                 logger.info(f"J-Quants: Loaded master data for {today}")
                 return resp["data"]
        except Exception:
            pass
        
        time.sleep(1) # Avoid rate limit

        # 2. Free Plan Fallback (13 weeks ago approx 90 days)
        # J-Quants Free Plan often has 12-week delay for some data, though Master data is usually open.
        # But "400 Subscription covers..." suggests date restriction.
        try:
            target_date = datetime.now() - timedelta(weeks=13)
            date_str = target_date.strftime("%Y%m%d")
            resp = self.get("/equities/master", {"date": date_str})
            if isinstance(resp, dict) and "data" in resp and resp["data"]:
                 logger.info(f"J-Quants: Loaded master data for {date_str} (Fallback 13w)")
                 return resp["data"]
        except Exception:
            pass
            
        time.sleep(1)

        # 3. Last 7 days (in case it was just a holiday and user HAS premium)
        for i in range(1, 8):
            target_date = datetime.now() - timedelta(days=i)
            date_str = target_date.strftime("%Y%m%d")
            try:
                resp = self.get("/equities/master", {"date": date_str})
                if isinstance(resp, dict) and "data" in resp and resp["data"]:
                     logger.info(f"J-Quants: Loaded master data for {date_str}")
                     return resp["data"]
            except Exception:
                pass
            time.sleep(1)
        
        # 4. Deep Fallback
        try:
             date_str = "20240104"
             resp = self.get("/equities/master", {"date": date_str})
             if isinstance(resp, dict) and "data" in resp and resp["data"]:
                 logger.info(f"J-Quants: Loaded master data for {date_str} (Deep Fallback)")
                 return resp["data"]
        except Exception as e:
             logger.error(f"J-Quants: Deep fallback failed: {e}")

        logger.error("J-Quants: Could not find valid master data.")
        return []

# Global instance
client = JQuantsClient()

