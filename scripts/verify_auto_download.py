import asyncio
import os
import shutil
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(os.getcwd())

from routers.fundamentals import get_edinet_fundamental

async def main():
    doc_id = "S100TK3X"
    doc_dir = Path(f"data/edinet/{doc_id}")
    
    # 1. Cleanup
    if doc_dir.exists():
        print(f"Removing existing {doc_dir}...")
        shutil.rmtree(doc_dir)
    
    if doc_dir.exists():
        print("Error: Failed to remove directory.")
        return

    # 2. Call API function (simulated)
    print(f"Calling get_edinet_fundamental({doc_id})...")
    try:
        result = await get_edinet_fundamental(doc_id)
        print("Success! Result keys:", result.keys())
        
        # 3. Verify download
        if doc_dir.exists():
            print("Verified: Document directory recreated.")
            if (doc_dir / "unzipped").exists():
                 print("Verified: Document unzipped.")
        else:
             print("Error: Document directory NOT created.")
             
        # Check financial data
        if result.get("financials"):
            rev = result["financials"].get("revenue")
            print(f"Financials extracted. Revenue: {rev}")
        else:
            print("Warning: No financials extracted.")
            
    except Exception as e:
        print(f"Error during execution: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
