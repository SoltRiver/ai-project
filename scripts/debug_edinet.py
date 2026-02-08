
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

from services.edinet_service import EdinetClient

def debug_edinet(ticker="7203"):
    print(f"--- Debugging EDINET for {ticker} ---")
    client = EdinetClient()
    
    # Check code mapping
    code = client.get_edinet_code(ticker)
    print(f"EDINET Code: {code}")
    
    if not code:
        print("Error: Could not resolve EDINET code.")
        return

    '''
    # Check search functionality
    print("Searching for Annual Report...")
    try:
        doc_id = client.search_annual_report(code)
        print(f"Found DocID: {doc_id}")
        
        if doc_id:
            print("Attempting download and parse...")
            data = client.download_and_parse(doc_id)
            print("Parsed Data:", data)
        else:
            print("No document found.")

    except Exception as e:
        print(f"EXCEPTION during search/download: {e}")
        import traceback
        traceback.print_exc()
    '''

    # Direct test for multiple dates
    print("\n--- Direct Test ---")
    for d_day in [25, 26, 27]:
        d = datetime(2024, 6, d_day)
        print(f"Testing {d.date()}...")
        found = client._scan_period("E02144", d, days=1)
        print(f"Result for {d.date()}: {found}")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "7203"
    debug_edinet(target)
