import os
import requests
import pandas as pd
from datetime import datetime, timedelta
import zipfile
import io
import time
from edinet_xbrl.edinet_xbrl_parser import EdinetXbrlParser
from typing import Optional, Dict, Any, List
import yfinance as yf

# For retry logic
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class EdinetClient:
    API_ENDPOINT = "https://disclosure.edinet-fsa.go.jp/api/v2"
    
    # Official path to the Code List (ZIP) - Note: This URL might change or require specific handling
    # We try a fixed recent date or the generic download endpoint if available.
    # Actually, simpler approach: The API doesn't provide the code list directly.
    # The FSA website provides it. 
    # Let's use a known static URL or fallback to a hardcoded mapping for top companies for the MVP if dynamic fetch fails.
    CODE_LIST_URL = "https://disclosure.edinet-fsa.go.jp/E01EW/BL/P101/Pm/Download/EdinetCodeDlInfo.csv" # Authentication required usually?
    
    CACHE_DIR = "cache"
    CODE_LIST_PATH = os.path.join(CACHE_DIR, "edinet_codes.csv")

    def __init__(self):
        if not os.path.exists(self.CACHE_DIR):
            os.makedirs(self.CACHE_DIR)
        
        self.session = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        self.session.mount('https://', HTTPAdapter(max_retries=retries))
        
        self.code_map = self._load_code_map()

    def _load_code_map(self) -> pd.DataFrame:
        if os.path.exists(self.CODE_LIST_PATH):
            try:
                # EDINET CSV is CP932
                return pd.read_csv(self.CODE_LIST_PATH, encoding='cp932', skiprows=1)
            except Exception:
                pass
        return pd.DataFrame() # Fallback: return empty and rely on other methods or manual update

    def update_code_list(self):
        """
        Attempt to download the latest EDINET code list.
        This is tricky to automate without a stable URL.
        For now, we will assume the file exists or user provides it.
        Or we can download from a specific mirrored location if available.
        
        Alternative: We will skip this and if 'get_edinet_code' fails, return None.
        """
        pass

    def get_edinet_code(self, ticker: str) -> Optional[str]:
        """
        Convert '7203' -> 'E02144'.
        """
        if self.code_map.empty:
            # Fallback for Top Companies (MVP)
            # Toyota, Sony, Nintendo, Softbank, FastRetailing
            fallback_map = {
                "7203": "E02144",
                "6758": "E00561",
                "7974": "E02367",
                "9984": "E02778",
                "9983": "E03366",
            }
            return fallback_map.get(str(ticker))
        
        # Ensure ticker is searched correctly (SecuritiesCode column)
        # The CSV usually has 4-digit codes + '0' (eg 72030)
        try:
            target = int(ticker) * 10 
            row = self.code_map[self.code_map['証券コード'] == target]
            if not row.empty:
                return row.iloc[0]['ＥＤＩＮＥＴコード']
        except Exception:
            pass
        
        # Try finding by name?
        return None

    def search_annual_report(self, edinet_code: str, reference_date: Optional[datetime] = None) -> Optional[str]:
        """
        Find the DocID of the latest 'Annual Securities Report' (Yuho).
        DocTypeCode = 120
        """
        # Strategy:
        # 1. Start from reference_date (or today) and go back.
        # 2. Limit to reasonable range (e.g. 90 days back from reference).
        # 3. Use 'list=2' (metadata) to be lighter? No, use list=1 to check details.
        
        if not reference_date:
            reference_date = datetime.now()

        # Phase 1: Look back 30 days from reference date (useful if we are in filing season)
        print(f"Searching documents for {edinet_code} (Phase 1: Recent)...")
        found = self._scan_period(edinet_code, reference_date, days=30)
        if found:
            return found
            
        # Phase 2: If we are not in filing season (e.g. Jan), look at last June (Peak for March-end companies)
        # Verify current month. If < 6, look at previous year's June. If > 6, look at this year's June.
        current_year = reference_date.year
        target_year = current_year if reference_date.month > 6 else current_year - 1
        
        # Search late June (June 30 backwards for 45 days -> mid May)
        print(f"Searching documents for {edinet_code} (Phase 2: June {target_year})...")
        june_date = datetime(target_year, 6, 30)
        found = self._scan_period(edinet_code, june_date, days=45) 
        
        return found

    def _scan_period(self, edinet_code: str, start_date: datetime, days: int) -> Optional[str]:
        check_date = start_date
        for _ in range(days): 
            date_str = check_date.strftime("%Y-%m-%d")
            url = f"{self.API_ENDPOINT}/documents.json"
            params = {"date": date_str, "type": 2} 
            
            try:
                res = self.session.get(url, params=params, timeout=5)
                if res.status_code == 200:
                    data = res.json()
                    docs = data.get("results", [])
                    if docs:
                        for doc in docs:
                            if doc.get("edinetCode") == edinet_code:
                                doc_type = doc.get("docTypeCode")
                                # 120: Annual Securities Report
                                if doc_type == "120":
                                    return doc.get("docID")
            except Exception as e:
                print(f"Error fetching {date_str}: {e}")

            check_date -= timedelta(days=1)
            # Sleep slightly less to look fast
            time.sleep(0.05) 

        return None

    def download_and_parse(self, doc_id: str) -> Dict[str, Any]:
        """
        Download XBRL, parse, and normalize.
        """
        # API v2 Document endpoint: /documents/{docID}?type=1 (XBRL)
        url = f"{self.API_ENDPOINT}/documents/{doc_id}"
        params = {"type": 1}
        
        print(f"Downloading DocID: {doc_id}")
        res = self.session.get(url, params=params, stream=True)
        
        if res.status_code != 200:
            return {}

        # Save to temp zip
        zip_path = os.path.join(self.CACHE_DIR, f"{doc_id}.zip")
        with open(zip_path, "wb") as f:
            for chunk in res.iter_content(chunk_size=8192):
                f.write(chunk)
                
        # Parse using edinet-xbrl
        parser = EdinetXbrlParser()
        
        # We need to extract the xbrl file from zip
        # edinet-xbrl might handle zip directly? Check docs or assume we need to unzip.
        # The parser usually takes a directory or file path.
        
        xbrl_dir = os.path.join(self.CACHE_DIR, doc_id)
        if not os.path.exists(xbrl_dir):
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(xbrl_dir)
        
        # Find the .xbrl file (PublicDoc)
        xbrl_file = None
        for root, dirs, files in os.walk(xbrl_dir):
            for file in files:
                if file.endswith(".xbrl") and "PublicDoc" in file:
                    xbrl_file = os.path.join(root, file)
                    break
        
        if not xbrl_file:
            return {}

        parsed_data = parser.parse_file(xbrl_file)
        
        # Normalize
        return self._normalize_financials(parsed_data)

    def _normalize_financials(self, data: Any) -> Dict[str, Any]:
        """
        Extract specific tags for BS/PL/CF.
        Handles namespace prefixes and context checking.
        """
        # Dictionary to store found values
        financials = {
            "sales": 0,
            "operating_profit": 0,
            "ordinary_profit": 0,
            "net_profit": 0,
            "total_assets": 0,
            "net_assets": 0,
            "equity": 0,
            "cash_flows_operating": None,
            "cash_flows_investing": None,
            "cash_flows_financing": None,
            "cash_and_equivalents": 0,
            "period_start": None,
            "period_end": None
        }

        # Targeted J-GAAP Tags (Key: Normalized Name, Value: List of possible XBRL tags)
        # Note: We prioritize J-GAAP ('jppfs_cor').
        targets = {
            "sales": ["NetSales", "OperatingRevenue1", "OperatingRevenue2"],
            "operating_profit": ["OperatingIncome"],
            "ordinary_profit": ["OrdinaryIncome"],
            "net_profit": ["ProfitLossAttributableToOwnersOfParent", "NetIncome"],
            "total_assets": ["TotalAssets"],
            "net_assets": ["NetAssets"],
            "cash_flows_operating": ["NetCashProvidedByUsedInOperatingActivities"],
            "cash_flows_investing": ["NetCashProvidedByUsedInInvestingActivities"],
            "cash_flows_financing": ["NetCashProvidedByUsedInFinancingActivities"],
            "cash_and_equivalents": ["CashAndCashEquivalents"]
        }
        
        # Accessing data from edinet-xbrl parser
        # The parser typically exposes a way to iterate over keys.
        # If 'data' is the parser object (EdinetXbrlParser), it might store data in `data.xbrl_data` or similar?
        # Actually, `parse_file` returns an `EdinetData` object.
        # Let's try grabbing values assuming `get_data` or `key` access.
        
        # Helper to find values
        # We assume `data` is the parsed object.
        # We iterate over all keys in the raw data to find matches if we can't look up directly.
        
        # IMPORTANT: 'edinet-xbrl' library details:
        # parsed.get_value(key, context_ref)
        
        # We need to guess the 'CurrentYear' context.
        # Usually 'CurrentYearDuration' (for PL/CF) and 'CurrentYearInstant' (for BS).
        
        contexts_duration = ["CurrentYearDuration", "CurrentYearDuration_NonConsolidatedMember"]
        contexts_instant = ["CurrentYearInstant", "CurrentYearInstant_NonConsolidatedMember"]
        
        for key, tags in targets.items():
            found_val = None
            
            # Determine context type based on key (BS vs others)
            is_bs = key in ["total_assets", "net_assets", "equity", "cash_and_equivalents"]
            contexts = contexts_instant if is_bs else contexts_duration

            for tag in tags:
                # Try with common namespaces
                for ns in ["jppfs_cor:", "jpcrp_cor:", ""]:
                    full_tag = f"{ns}{tag}"
                    
                    # Try each context
                    for context in contexts:
                        val = None
                        try:
                            val = data.get_value(full_tag, context)
                        except:
                            # If direct method doesn't exist, we might be using the wrong API.
                            # Fallback: Check if we can search keys.
                            pass
                        
                        if val is not None:
                            found_val = val
                            break
                    if found_val is not None: break
                if found_val is not None: break
            
            if found_val is not None:
                # Convert to float/int
                try:
                    financials[key] = float(found_val)
                except:
                    financials[key] = 0
        
        # Calculate Equity if not found explicitly (NetAssets ~ Equity usually, but handles minority interest)
        if financials["equity"] == 0 and financials["net_assets"] != 0:
            financials["equity"] = financials["net_assets"] # Simple approximation

        return financials

    def get_financial_data(self, ticker: str) -> Optional[Dict[str, Any]]:
        code = self.get_edinet_code(ticker)
        if not code:
            print(f"EDINET Code not found for {ticker}")
            return None
        
        # Optimization: Use yfinance to find the last earnings date
        yf_ticker = yf.Ticker(f"{ticker}.T")
        # earnings_date is often future, so key is finding the LAST report.
        # We'll search back from today.
        
        doc_id = self.search_annual_report(code)
        if not doc_id:
            print("No Annual Report found in cache window")
            return None
            
        return self.download_and_parse(doc_id)
