
from typing import Dict, Any, Optional

class FundamentalRatios:
    def calculate_ratios(self, financials: Dict[str, Any], market: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate key financial ratios.
        """
        ratios = {
            "per": None,
            "pbr": None,
            "roe": None,
            "eps": None,
            "bps": None
        }
        
        if not financials or not market:
            return ratios
            
        # Extract values
        price = market.get("price")
        shares = market.get("shares_outstanding")
        
        net_profit = financials.get("net_profit")
        net_assets = financials.get("net_assets")
        equity = financials.get("equity") # Usually same as net_assets for simplified view
        
        # Calculate BPS / EPS first
        if shares and shares > 0:
            if net_profit is not None:
                ratios["eps"] = net_profit / shares
            if net_assets is not None:
                ratios["bps"] = net_assets / shares
                
        # Calculate PER / PBR
        if price and price > 0:
            if ratios["eps"] and ratios["eps"] > 0:
                ratios["per"] = price / ratios["eps"]
            if ratios["bps"] and ratios["bps"] > 0:
                ratios["pbr"] = price / ratios["bps"]
                
        # Calculate ROE
        if net_profit is not None and equity is not None and equity > 0:
            ratios["roe"] = net_profit / equity
            
        return ratios
