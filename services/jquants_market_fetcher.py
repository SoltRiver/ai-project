
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from services.jquants_client import client as jquants_client

logger = logging.getLogger(__name__)

class JQuantsMarketFetcher:
    def __init__(self):
        self.client = jquants_client

    def get_market_data(self, sec_code: str, target_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch market data (price, shares, etc.) for a specific code and date.
        If target_date is None, fetches latest.
        """
        market_data = {
            "price": None,
            "shares_outstanding": None,
            "market_cap": None,
            "eps": None, # J-Quants might not provide dynamic EPS easily in free tier, simplified to None
            "bps": None,
            "price_date": None
        }

        try:
            # 1. Get Shares Outstanding from /listed/info
            # Note: This API returns list. We filter by code. 
            # In free tier, we might assume it returns valid data for the requested code.
            # However, /listed/info with code param is efficient.
            info_resp = self.client.get_listed_info(code=sec_code)
            shares = None
            if info_resp and "info" in info_resp:
                # info is list
                items = info_resp["info"]
                if items:
                    # Take the latest record if multiple? Usually 1 per code if specific code queried
                    latest_info = items[0] 
                    # Key might be "NumberOfIssuedShares" (Common)
                    # Let's try to parse
                    val = latest_info.get("NumberOfIssuedShares")
                    if val:
                        shares = float(val)
                        market_data["shares_outstanding"] = shares

            # 2. Get Price (Daily Quotes)
            # Strategy: Fetch range [target - 7 days, target] to find closest previous business day
            # If target_date is None, fetch recent data (e.g. last 7 days from today)
            
            if target_date:
                t_date = datetime.strptime(target_date, "%Y-%m-%d")
                t_date_str = targets_to = t_date.strftime("%Y%m%d")
                t_from = (t_date - timedelta(days=7)).strftime("%Y%m%d")
            else:
                t_date = datetime.now()
                t_date_str = targets_to = t_date.strftime("%Y%m%d")
                t_from = (t_date - timedelta(days=7)).strftime("%Y%m%d")

            quotes_resp = self.client.get_daily_quotes(code=sec_code, from_date=t_from, to_date=targets_to)
            quotes = []
            if quotes_resp and "daily_quotes" in quotes_resp:
                 quotes = quotes_resp["daily_quotes"]
            
            if quotes:
                # Sort by Date descending to get proper 'latest' or 'closest to target'
                # J-Quants Date format: "YYYY-MM-DD" or "YYYYMMDD"? usually "YYYY-MM-DD" in response
                quotes.sort(key=lambda x: x.get("Date", ""), reverse=True)
                
                # Pick the latest in the range (which is closest to target_to)
                latest_quote = quotes[0]
                
                # Close price
                close_price = latest_quote.get("Close")
                if close_price:
                    market_data["price"] = float(close_price)
                    market_data["price_date"] = latest_quote.get("Date")

            # 3. Calculate Market Cap
            if market_data["price"] and market_data["shares_outstanding"]:
                market_data["market_cap"] = market_data["price"] * market_data["shares_outstanding"]

        except Exception as e:
            logger.error(f"Error checking J-Quants market data for {sec_code}: {e}")
            
        return market_data
