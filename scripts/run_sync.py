
import sys
import os
import time
import logging

# Add project root to sys.path
sys.path.append(os.getcwd())

# Configure logging to stdout
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from services.stock_master_service import stock_master_service

def run_sync():
    print("--- Starting Manual J-Quants V2 Sync ---")
    print("Waiting 5 seconds to cool down API rate limit...")
    time.sleep(5)
    
    try:
        # Force sync even if already synced today (to verify V2 works)
        # But `initialize_and_sync` checks date.
        # We should call `_sync_from_jquants` directly? 
        # No, let's call `initialize_and_sync` but maybe delete the `AppSyncStatus` record first?
        # Or just trust that if it fails it will retry or we can modify the service to force it.
        # Actually `stock_master_service._sync_from_jquants()` is what we want to test.
        # But it's internal.
        # Let's use `initialize_and_sync`. 
        # To ensure it runs, we can manually delete the sync status record in DB first if needed, 
        # but if previous attempts failed (as per logs), the status is FAILED or old.
        # So `initialize_and_sync` SHOULD try again.
        
        stock_master_service.initialize_and_sync()
        print("--- Sync Process Completed (Check logs above) ---")
        
        # Verify result immediately
        from database import SessionLocal
        from models.master import StockMaster
        db = SessionLocal()
        count = db.query(StockMaster).count()
        print(f"Total Stock Master Records: {count}")
        db.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_sync()
