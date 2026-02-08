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
        # 2. Fetch Financial Data (XBRL)
        # Try to find recent annual report (Yearly)
        # Assuming ticker can be used as edinet_code for search_annual_report
        edinet_code = ticker 
        doc_id = self.edinet_client.search_annual_report(edinet_code)
        
        financials = None
        has_financials = False
        source = "EDINET"
        fallback_reason = None
        
        if doc_id:
            print(f"DEBUG: Found Annual Report {doc_id}")
            financials = self.edinet_client.get_financial_data(doc_id)
            if financials:
                # Initialize analysis dictionary here, after financials are potentially found
                analysis = {
                    "symbol": ticker,
                    "financials": financials,
                    "market": market_info,
                    "indicators": {}
                }
                has_financials = True
        
        if not has_financials:
            # Initialize analysis dictionary here if EDINET data was not found
            analysis = {
                "symbol": ticker,
                "financials": None, # Will be populated by fallback if successful
                "market": market_info,
                "indicators": {}
            }

            # Determine reason for fallback
            if not self.edinet_client.api_key:
                 fallback_reason = "API Key Missing"
            elif self.edinet_client._api_access_denied:
                fallback_reason = "Auth Error (401)"
            elif not doc_id:
                fallback_reason = "Document Not Found"
            else:
                fallback_reason = "XBRL Parsing Failed"

            # Fallback to yfinance data if available in market_info
            if market_info:
                print(f"Fallback: Using yfinance data for {ticker}")
                source = "Fallback(yfinance)"
                
                # Map yfinance keys to expected keys
                sales = market_info.get("total_revenue")
                net = market_info.get("net_income")
                b_val = market_info.get("book_value")
                shares = market_info.get("shares_outstanding")
                op_margin = market_info.get("operating_margins")

                if sales or net or b_val:
                    financials = {
                        "sales": sales or 0,
                        "operating_profit": (sales or 0) * (op_margin or 0),
                        "ordinary_profit": 0, 
                        "net_profit": net or 0,
                        "total_assets": 0, 
                        "equity": (b_val or 0) * (shares or 0),
                        "cash_flows_operating": market_info.get("operating_cashflow"),
                        "cash_flows_investing": None,
                        "cash_flows_financing": None,
                        "cash_and_equivalents": 0,
                    }
                    
                    roa = market_info.get("return_on_assets")
                    if roa and roa > 0 and financials["net_profit"]:
                        financials["total_assets"] = financials["net_profit"] / roa

                    analysis["financials"] = financials
                    has_financials = True
        
        # Fallback if yfinance shares is missing (rare)
        if not shares_outstanding and has_financials:
            # Maybe try to find shares in XBRL? Ignored for MVP.
            pass

        analysis["source"] = source
        analysis["fallback_reason"] = fallback_reason

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
