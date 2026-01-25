from typing import Dict, Any, Optional
from services.edinet_service import EdinetClient
from services.data_fetcher import get_latest_price, fetch_stock_info

class FinancialAnalyzer:
    def __init__(self):
        self.edinet_client = EdinetClient()

    def analyze_stock(self, ticker: str) -> Dict[str, Any]:
        """
        Get full analysis: Realtime indicators based on Official EDINET Financials.
        """
        # 1. Get Financials (Annual)
        financials = self.edinet_client.get_financial_data(ticker)
        has_financials = financials is not None
        
        # 2. Get Market Data (Price, Shares)
        market_info = fetch_stock_info(f"{ticker}.T")
        if not market_info:
            market_info = {}
        current_price = market_info.get("current_price")
        # Try to get shares_outstanding from market_info (requires update in data_fetcher or it might be there)
        shares_outstanding = market_info.get("shares_outstanding")
        
        # Fallback if yfinance shares is missing (rare)
        if not shares_outstanding and has_financials:
            # Maybe try to find shares in XBRL? Ignored for MVP.
            pass

        analysis = {
            "symbol": ticker,
            "financials": financials,
            "market": market_info,
            "indicators": {}
        }

        if not has_financials:
            analysis["error"] = "財務データが見つかりませんでした (EDINET document not found)"
            return analysis
            
        # 3. Calculate Indicators
        # Normalize units: EDINET 'Sales' is usually raw Yen.
        
        net_income = financials.get("net_profit", 0)
        equity = financials.get("equity", 0)
        total_assets = financials.get("total_assets", 0)
        
        # Indicators
        roe = (net_income / equity) * 100 if equity else None
        roa = (net_income / total_assets) * 100 if total_assets else None
        equity_ratio = (equity / total_assets) * 100 if total_assets else None
        
        # per_share
        eps = None
        bps = None
        per = None
        pbr = None
        
        if shares_outstanding:
            eps = net_income / shares_outstanding
            bps = equity / shares_outstanding
            
            if current_price:
                per = current_price / eps if eps > 0 else None
                pbr = current_price / bps if bps > 0 else None

        analysis["indicators"] = {
            "ROE": roe,
            "ROA": roa,
            "EquityRatio": equity_ratio,
            "EPS": eps,
            "BPS": bps,
            "PER": per,
            "PBR": pbr,
            "DividendYield": market_info.get("dividend_yield"), # Use yfinance for yield
            "Price": current_price
        }

        return analysis

    def format_analysis(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        # Placeholder for data shaping for frontend if needed
        # Returning dict is fine for Jinja2
        return analysis
