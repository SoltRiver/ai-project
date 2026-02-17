import sys
import os
sys.path.insert(0, ".")

from services.edinet_document_store import EdinetDocumentStore
from services.edinet_xbrl_locator import EdinetXbrlLocator
from services.edinet_fin_extract import EdinetFinancialExtractor
import asyncio
import logging

logging.basicConfig(level=logging.INFO)

async def test_extraction(doc_id):
    print(f"Testing dividend extraction for DocID: {doc_id}")
    store = EdinetDocumentStore()
    
    # Try to extract (assumes already downloaded based on folder presence)
    try:
        unzipped_dir = store.extract_document(doc_id)
    except ValueError:
        print("Document not found locally.")
        return

    locator = EdinetXbrlLocator()
    location_result = await locator.locate_xbrl_files(unzipped_dir)
    primary_xbrl = location_result.get("primary_xbrl")
    
    if not primary_xbrl:
        print("Primary XBRL not found.")
        return

    print(f"Primary XBRL: {primary_xbrl}")

    extractor = EdinetFinancialExtractor()
    financials = extractor.extract_financials(primary_xbrl)
    
    print("\n--- Financials ---")
    # Check keys added
    keys = ["sec_code", "filer_name", "period_end", "dividend_total", "dividend_per_share"]
    for k in keys:
        print(f"{k}: {financials.get(k)}")

    # Check validity
    if financials.get("dividend_total") is not None or financials.get("dividend_per_share") is not None:
        print("\nSUCCESS: Dividend data tag found.")
    else:
        print("\nRESULT: Dividend data is None (might be unavailable in this specific report).")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        doc_ids = sys.argv[1:]
    else:
        # Default to local ones found
        doc_ids = ["S100TK3X", "S100TR7I"]
    
    for doc_id in doc_ids:
        print(f"\nProcessing {doc_id}...")
        asyncio.run(test_extraction(doc_id))
