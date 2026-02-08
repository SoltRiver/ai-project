
from edinet_xbrl.edinet_xbrl_parser import EdinetXbrlParser
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

class EdinetFinancialExtractor:
    def __init__(self):
        self.parser = EdinetXbrlParser()
        
    def extract_financials(self, xbrl_path: str) -> Dict[str, Any]:
        """
        Extract key financial metrics from XBRL file.
        """
        financials = {
            "revenue": None,
            "operating_profit": None,
            "ordinary_profit": None,
            "net_profit": None,
            "total_assets": None,
            "net_assets": None,
            "equity": None,
            "cash_flows_operating": None,
            "cash_flows_investing": None,
            "cash_flows_financing": None,
            "cash_and_equivalents": None,
            "period_start": None,
            "period_end": None
        }
        
        if xbrl_path.endswith(".htm") or xbrl_path.endswith(".html"):
            logger.warning(f"Attempting to extract from Inline XBRL (.htm): {xbrl_path}")
            # Continue to try parsing, as edinet-xbrl might handle it via BeautifulSoup


        try:
            edinet_data = self.parser.parse_file(xbrl_path)
            
            # Helper to find value from list of candidate tags
            def find_value(tags: List[str], context_ref: str) -> Optional[float]:
                for tag in tags:
                    namespaces = ["jppfs_cor:", "jpcrp_cor:", ""]
                    for ns in namespaces:
                        full_key = f"{ns}{tag}"
                        
                        # Check availability of get_value (v2 object vs v3 object)
                        if hasattr(edinet_data, "get_value"):
                             val = edinet_data.get_value(full_key, context_ref)
                             if val is not None:
                                try:
                                    return float(val)
                                except:
                                    continue
                        
                        # Fallback for some versions of edinet-xbrl if get_value is missing
                        # Inspect data list if available
                        elif hasattr(edinet_data, "get_data_list"):
                             data_list = edinet_data.get_data_list(full_key)
                             for item in data_list:
                                 # Check context manually? 
                                 # Item might have .context_ref property
                                 if hasattr(item, "context_ref") and item.context_ref == context_ref:
                                      if hasattr(item, "get_value"):
                                           v = item.get_value()
                                           try: return float(v)
                                           except: continue
                                      elif hasattr(item, "value"):
                                           v = item.value
                                           try: return float(v)
                                           except: continue
                                 
                return None

            # Contexts (Standard J-GAAP)
            ctx_duration = "CurrentYearDuration"
            ctx_instant = "CurrentYearInstant"
            
            # Map
            targets_duration = {
                "revenue": ["NetSales", "OperatingRevenue1", "OperatingRevenue2"],
                "operating_profit": ["OperatingIncome"],
                "ordinary_profit": ["OrdinaryIncome"],
                "net_profit": ["ProfitLossAttributableToOwnersOfParent", "NetIncome"],
                "cash_flows_operating": ["NetCashProvidedByUsedInOperatingActivities"],
                "cash_flows_investing": ["NetCashProvidedByUsedInInvestingActivities"],
                "cash_flows_financing": ["NetCashProvidedByUsedInFinancingActivities"],
            }
            
            targets_instant = {
                "total_assets": ["TotalAssets"],
                "net_assets": ["NetAssets"],
                "cash_and_equivalents": ["CashAndCashEquivalents"],
            }
            
            # Extract Duration Items
            for key, tags in targets_duration.items():
                val = find_value(tags, ctx_duration)
                if val is None:
                    # Try NonConsolidated
                    val = find_value(tags, "CurrentYearDuration_NonConsolidatedMember")
                financials[key] = val

            # Extract Instant Items
            for key, tags in targets_instant.items():
                val = find_value(tags, ctx_instant)
                if val is None:
                    val = find_value(tags, "CurrentYearInstant_NonConsolidatedMember")
                financials[key] = val
                
            # Equity = NetAssets (Simplified)
            if financials["equity"] is None and financials["net_assets"] is not None:
                financials["equity"] = financials["net_assets"]

        except Exception as e:
            logger.error(f"Failed to extract financials from {xbrl_path}: {e}")
            financials["error"] = str(e)
            
        return financials
