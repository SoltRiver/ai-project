import os
import requests
import pandas as pd
from datetime import datetime, timedelta
import zipfile
import io
import time
from functools import lru_cache
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
        
        self.api_key = os.environ.get("EDINET_API_KEY")
        if not self.api_key:
            print("WARNING: EDINET_API_KEY not found in environment variables.")

        # Integration with Storage Service
        from services.edinet_storage import EdinetStorageService
        try:
             self.storage = EdinetStorageService()
        except Exception as e:
             # Fallback if DB not ready (e.g. during tests)
             print(f"EdinetStorageService init failed: {e}")
             self.storage = None

        self.code_map = self._load_code_map()
        self._api_access_denied = False

    def _check_api_access(self) -> bool:
        if self._api_access_denied:
            print("EDINET API Access previously denied. Skipping.")
            return False
        return True

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
                "8306": "E03606", # Mitsubishi UFJ
                "8316": "E03614", # Sumitomo Mitsui
                "8411": "E03615", # Mizuho
                "8035": "E01913", # Tokyo Electron
                "6861": "E02008", # Keyence
                "6098": "E05617", # Recruit
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

        # Optimization: Fixed filing dates for major companies to avoid scanning
        # Dates are for 2024 filings (FY2023). 
        # In a real app, this should be a DB or dynamic lookup.
        FIXED_FILING_DATES = {
            "E02144": "2024-06-25", # Toyota
            "E00561": "2024-06-26", # Sony
            "E02778": "2024-06-21", # Softbank Group
            "E03606": "2024-06-25", # MUFG
            "E03614": "2024-06-21", # Sumitomo Mitsui
            "E03615": "2024-06-20", # Mizuho
            "E01913": "2024-06-21", # Tokyo Electron
            "E02367": "2024-06-27", # Nintendo
            "E02008": "2024-06-14", # Keyence
            "E05617": "2024-06-20", # Recruit
        }

        if edinet_code in FIXED_FILING_DATES:
            print(f"Using fixed filing date for {edinet_code}")
            fixed_date = datetime.strptime(FIXED_FILING_DATES[edinet_code], "%Y-%m-%d")
            # Start 5 days after and scan back 10 days to cover a range around the date
            start_date = fixed_date + timedelta(days=5)
            found = self._scan_period(edinet_code, start_date, days=10)
            if found:
                return found

        # Phase 1: Look back 30 days from reference date (useful if logic is run in filing season)
        print(f"Searching documents for {edinet_code} (Phase 1: Recent)...")
        found = self._scan_period(edinet_code, reference_date, days=5) # Reduced from 30
        if found:
            return found
            
        # Phase 2: Look at last June
        current_year = reference_date.year
        target_year = current_year if reference_date.month > 6 else current_year - 1
        
        # Search late June (June 30 backwards)
        print(f"Searching documents for {edinet_code} (Phase 2: June {target_year})...")
        june_date = datetime(target_year, 6, 30)
        found = self._scan_period(edinet_code, june_date, days=14) # Reduced from 45
        
        return found

    # Mocking for Development (if valid API key is missing)
    SIMULATE_EDINET_SUCCESS = False # Set to True to test flow without API key
    def _scan_period(self, edinet_code: str, date: datetime, days: int = 1) -> Optional[str]:
        """
        Scan a period for Annual Securities Reports (Code 120).
        Retries up to 'days' back from 'date'.
        """
        if self.SIMULATE_EDINET_SUCCESS:
             print(f"DEBUG: Mock Mode ON. Checking code: {edinet_code}")
             if edinet_code == "E02144":
                 print(f"DEBUG: Simulating EDINET Search Success for {edinet_code}")
                 return "S100TR7I"
             else:
                 print(f"DEBUG: Code mismatch {edinet_code} != E02144")

        if not self._check_api_access():
             return None

        for i in range(days):
            target_date = date - timedelta(days=i)
            # Skip weekends if desired, but API works on weekends too usually.
            
            date_str = target_date.strftime("%Y-%m-%d")
            url = f"{self.API_ENDPOINT}/documents.json"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            if self.api_key:
                headers["Ocp-Apim-Subscription-Key"] = self.api_key
            
            params = {"date": date_str, "type": 1} 
            try:
                # print(f"DEBUG: Requesting {url} with params={params}")
                res = self.session.get(url, params=params, headers=headers, timeout=10)
                
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
                    else:
                        if "statusCode" in res.text and "401" in res.text:
                            print("WARNING: EDINET API Access Denied (Missing/Invalid Key). Switching to fallback mode.")
                            self._api_access_denied = True
                            return None
                elif res.status_code == 401:
                    print(f"WARNING: EDINET API Returned 401 Unauthorized.")
                    self._api_access_denied = True
                    return None
                else:
                    print(f"WARNING: EDINET API Error: {res.status_code}")

            except Exception as e:
                print(f"Error checking {date_str}: {e}")



        return None

    def get_documents_by_date(self, date_obj: datetime, type_code: int = 2) -> List[Dict[str, Any]]:
        """
        Public wrapper for /documents.json endpoint.
        Returns list of document objects.
        """
        if not self._check_api_access():
             return []

        date_str = date_obj.strftime("%Y-%m-%d")
        url = f"{self.API_ENDPOINT}/documents.json"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        if self.api_key:
            headers["Ocp-Apim-Subscription-Key"] = self.api_key
        
        params = {"date": date_str, "type": type_code} 
        try:
            res = self.session.get(url, params=params, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                return data.get("results", [])
            elif res.status_code == 401:
                print(f"WARNING: EDINET API Returned 401 Unauthorized.")
                self._api_access_denied = True
                return []
            else:
                print(f"WARNING: EDINET API Error: {res.status_code}")
                return []
        except Exception as e:
            print(f"Error getting documents for {date_str}: {e}")
            return []

    def _download_document(self, doc_id: str) -> Optional[str]:
        """
        Download the document (zip) and return file path.
        """
        if self.SIMULATE_EDINET_SUCCESS and doc_id == "S100TR7I":
            import os
            mock_path = os.path.abspath(os.path.join("cache", "S100TR7I.zip"))
            if os.path.exists(mock_path):
                 print(f"DEBUG: Simulating Download using local file: {mock_path}")
                 return mock_path

        if not self._check_api_access():
             return None

        url = f"{self.API_ENDPOINT}/documents/{doc_id}"
        params = {"type": 1} # 1: XBRL/ZIP
        headers = {"User-Agent": self.USER_AGENT, "Ocp-Apim-Subscription-Key": self.api_key}
        
        try:
            print(f"Downloading EDINET document {doc_id}...")
            res = self.session.get(url, params=params, headers=headers, stream=True, timeout=30)
            
            if res.status_code == 200:
                filename = f"{doc_id}.zip"
                filepath = os.path.join(self.CACHE_DIR, filename)
                
                with open(filepath, "wb") as f:
                    for chunk in res.iter_content(chunk_size=8192):
                        f.write(chunk)
                return filepath
            else:
                print(f"Failed to download {doc_id}: {res.status_code}")
                return None
        except Exception as e:
            print(f"Error downloading {doc_id}: {e}")
            return None

    def fetch_document_content_zip(self, doc_id: str) -> Optional[bytes]:
        """
        Fetch ZIP content (type=1) for a doc_id.
        Returns binary content or None.
        """
        if self.SIMULATE_EDINET_SUCCESS and doc_id == "S100TR7I":
            import os
            mock_path = os.path.abspath(os.path.join("cache", "S100TR7I.zip"))
            if os.path.exists(mock_path):
                 with open(mock_path, "rb") as f:
                     return f.read()

        if not self._check_api_access():
             return None

        url = f"{self.API_ENDPOINT}/documents/{doc_id}"
        params = {"type": 1} # 1: XBRL/ZIP
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        if self.api_key:
             headers["Ocp-Apim-Subscription-Key"] = self.api_key
        
        try:
            print(f"Fetching content for {doc_id}...")
            res = self.session.get(url, params=params, headers=headers, timeout=60)
            if res.status_code == 200:
                return res.content
            else:
                print(f"Failed to fetch content {doc_id}: {res.status_code}")
                return None
        except Exception as e:
            print(f"Error fetching content {doc_id}: {e}")
            return None

    def fetch_document_content_pdf(self, doc_id: str) -> Optional[bytes]:
        """
        Fetch PDF content (type=2) for a doc_id.
        Returns binary content or None.
        """
        if not self._check_api_access():
             return None

        url = f"{self.API_ENDPOINT}/documents/{doc_id}"
        params = {"type": 2} # 2: PDF
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        if self.api_key:
             headers["Ocp-Apim-Subscription-Key"] = self.api_key
        
        try:
            print(f"Fetching PDF content for {doc_id}...")
            res = self.session.get(url, params=params, headers=headers, timeout=60)
            if res.status_code == 200:
                return res.content
            else:
                print(f"Failed to fetch PDF {doc_id}: {res.status_code}")
                return None
        except Exception as e:
            print(f"Error fetching PDF {doc_id}: {e}")
            return None

    def download_and_parse(self, doc_id: str) -> Dict[str, Any]:
        """
        Download XBRL, parse, and normalize.
        """
        # API v2 Document endpoint: /documents/{docID}?type=1 (XBRL)
        # Delegate download to helper (which supports caching and mocking)
        zip_path = self._download_document(doc_id)
        if not zip_path:
             return {}
                
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
                # XBRL files can be .xbrl or .xml (inline XBRL)
                # Usually located in a folder named 'PublicDoc'
                if (file.endswith(".xbrl") or file.endswith(".xml")) and "PublicDoc" in root:
                    # Avoid manifest files
                    if "manifest" in file: continue
                    xbrl_file = os.path.join(root, file)
                    break
            if xbrl_file: break
        
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
        # Targeted IFRS/J-GAAP Tags
        targets = {
            "sales": ["NetSales", "OperatingRevenue1", "OperatingRevenue2", 
                      "RevenuesUSGAAPSummaryOfBusinessResults", "NetSalesSummaryOfBusinessResults", # J-GAAP/USGAAP
                      "SalesRevenuesIFRS", "OperatingRevenuesIFRSKeyFinancialData"], # IFRS
            "operating_profit": ["OperatingIncome", "OperatingIncomeLoss", 
                                 "OperatingProfitLossIFRS"], # IFRS
            "ordinary_profit": ["OrdinaryIncome", "OrdinaryIncomeLoss",
                                "ProfitLossBeforeTaxIFRS", # Approx for IFRS
                                "ProfitLossBeforeTaxUSGAAPSummaryOfBusinessResults"],
            "net_profit": ["ProfitLossAttributableToOwnersOfParent", "NetIncome", 
                           "ProfitLossAttributableToOwnersOfParentIFRS", # IFRS
                           "NetIncomeLossSummaryOfBusinessResults"],
            "total_assets": ["TotalAssets", "TotalAssetsIFRSSummaryOfBusinessResults", "TotalAssetsUSGAAPSummaryOfBusinessResults", "AssetsIFRS"],
            "net_assets": ["NetAssets", "EquityIFRS", "EquityAttributableToOwnersOfParentIFRS"],
            "cash_flows_operating": ["NetCashProvidedByUsedInOperatingActivities", "NetCashProvidedByUsedInOperatingActivitiesIFRS"],
            "cash_flows_investing": ["NetCashProvidedByUsedInInvestingActivities", "NetCashProvidedByUsedInInvestingActivitiesIFRS"],
            "cash_flows_financing": ["NetCashProvidedByUsedInFinancingActivities", "NetCashProvidedByUsedInFinancingActivitiesIFRS"],
            "cash_and_equivalents": ["CashAndCashEquivalents", "CashAndCashEquivalentsIFRS"]
        }
        
        contexts_duration = ["CurrentYearDuration", "CurrentYearDuration_NonConsolidatedMember"]
        contexts_instant = ["CurrentYearInstant", "CurrentYearInstant_NonConsolidatedMember"]
        
        # Helper to extract value safely
        def extract_value(key_list, ctx_list):
            for tag in key_list:
                for ns in ["jppfs_cor:", "jpcrp_cor:", "jpcrp030000-asr_e02144-000:", ""]:
                    full_tag = f"{ns}{tag}"
                    
                    # Method 1: Direct get_value matching context list
                    for context in ctx_list:
                        try:
                            val = data.get_value(full_tag, context)
                            if val is not None: return val
                        except: pass
                    
                    # Method 2: Fuzzy Context Search via get_data_list
                    if hasattr(data, "get_data_list"):
                        items = data.get_data_list(full_tag)
                        for item in items:
                            ctx = getattr(item, "context_ref", "")
                            # Prioritize Current Year (exclude Prior)
                            if "CurrentYear" in ctx and "Prior" not in ctx:
                                v = item.get_value() if hasattr(item, "get_value") else getattr(item, "value", None)
                                if v is not None: return v
            return None

        # Main Extraction Loop
        for key, tags in targets.items():
            # Determine suitable contexts
            is_bs = key in ["total_assets", "net_assets", "equity", "cash_and_equivalents"]
            contexts = contexts_instant if is_bs else contexts_duration
            
            val = extract_value(tags, contexts)
            
            if val is not None:
                try:
                    financials[key] = float(val)
                except:
                    financials[key] = 0
            else:
                financials[key] = 0
        
        # Calculate Equity if not found explicitly (NetAssets ~ Equity usually, but handles minority interest)
        if financials["equity"] == 0 and financials["net_assets"] != 0:
            financials["equity"] = financials["net_assets"] # Simple approximation

        return financials

    @lru_cache(maxsize=32)
    def get_financial_data(self, ticker: str) -> Optional[Dict[str, Any]]:
        code = self.get_edinet_code(ticker)
        if not code:
            print(f"EDINET Code not found for {ticker}")
            return None
        
        # Optimization: Use yfinance to find the last earnings date
        # yf_ticker = yf.Ticker(f"{ticker}.T")
        # earnings_date is often future, so key is finding the LAST report.
        # We'll search back from today.
        
        doc_id = self.search_annual_report(code)
        if not doc_id:
            print("No Annual Report found in cache window")
            return None
            
        return self.download_and_parse(doc_id)

    def fetch_edinet_code_list(self) -> Optional[str]:
        """
        Fetch EdinetCodeDlInfo.csv.
        Uses EdinetStorageService to save as 'CODE_LIST_{YYYYMMDD}'
        Returns absolute path to the extracted CSV file.
        """
        # Determine DocID based on today (or recent static URL)
        # We use today's date for versioning.
        now = datetime.now()
        doc_id = f"CODE_LIST_{now.strftime('%Y%m%d')}"
        
        # Check if already exists in storage
        if self.storage:
            record = self.storage.get_file_record(doc_id, "ZIP_TYPE5")
            if record and record.status == "OK":
                # Already downloaded, check extracted
                # We need to find where it is extracted.
                # Since EdinetStorageService only handles RAW, we need to handle extraction.
                # Reconstruct path
                raw_zip = self.storage.get_absolute_path(record.storage_path)
                extract_dir = raw_zip.parent.parent / "extracted" / "type5"
                csv_path = extract_dir / "EdinetcodeDlInfo.csv"
                if csv_path.exists():
                    return str(csv_path)

        # Download
        url = self.CODE_LIST_URL
        try:
            print(f"Downloading EDINET Code List from {url}...")
            # For MVP, if URL is protected, we might need to mock or use alternative
            # Just try standard download.
            res = self.session.get(url, timeout=60)
            if res.status_code != 200:
                print(f"Failed to download Code List: {res.status_code}")
                return None
            
            content = res.content
            print(f"Downloaded content size: {len(content)} bytes")
            print(f"First 10 bytes: {content[:10]}")
            
            # Check for HTML error page
            if content.strip().startswith(b"<!DOCTYPE") or b"<html" in content[:100].lower():
                print("Downloaded content appears to be HTML (likely error page). Skipping.")
                return None
            
            # Check if it is a ZIP (Magic bytes PK)
            import io
            import zipfile
            
            is_zip = content.startswith(b'PK')
            print(f"is_zip: {is_zip}")
            
            if not is_zip:
                # It's likely raw CSV. We must ZIP it to comply with "edinet_type5.zip" spec.
                # Create in-memory zip
                print("Content is not ZIP, creating ZIP wrapper...")
                mem_zip = io.BytesIO()
                with zipfile.ZipFile(mem_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
                    # Determine filename inside zip
                    zf.writestr('EdinetcodeDlInfo.csv', content)
                content = mem_zip.getvalue()
                print(f"Created ZIP wrapper size: {len(content)} bytes")
            
            # Save using Storage Service
            if self.storage:
                self.storage.save_raw_file(doc_id, now, "ZIP_TYPE5", content)
                
                # Extract
                # Get path again to be safe
                record = self.storage.get_file_record(doc_id, "ZIP_TYPE5")
                raw_zip = self.storage.get_absolute_path(record.storage_path)
                
                extract_dir = raw_zip.parent.parent / "extracted" / "type5"
                extract_dir.mkdir(parents=True, exist_ok=True)
                
                import zipfile
                with zipfile.ZipFile(raw_zip, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                    
                csv_path = extract_dir / "EdinetcodeDlInfo.csv"
                if csv_path.exists():
                    logger.info(f"EDINET Code List saved to {csv_path}")
                    return str(csv_path)
            
        except Exception as e:
            print(f"Error fetching code list: {e}")
            return None
        return None
