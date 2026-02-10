import sys
import os

# Add project root to sys.path
sys.path.append(os.getcwd())

from database import SessionLocal
from models.master import StockMaster, AppSyncStatus
from services.stock_master_service import stock_master_service

def verify_stock_master():
    print("--- Verifying Stock Master DB ---")
    db = SessionLocal()
    try:
        # 1. Check Record Count
        count = db.query(StockMaster).count()
        print(f"Total Stock Master Records: {count}")
        if count == 0:
            print("[FAIL] Stock Master is empty!")
            return
        else:
            print(f"[PASS] Stock Master populated (Count: {count})")

        # 2. Check Specific Record (Toyota)
        toyota = db.query(StockMaster).get("7203")
        if toyota:
            print(f"[PASS] Found Toyota: {toyota.code} - {toyota.name} ({toyota.market})")
        else:
            print("[FAIL] Toyota (7203) not found!")

        # 3. Check Sync Status
        sync_status = db.query(AppSyncStatus).first()
        if sync_status:
            print(f"[INFO] Last Sync: {sync_status.last_synced_at}")
            print(f"[INFO] Status: {sync_status.last_sync_status}")
            print(f"[INFO] Source: {sync_status.source}")
            if sync_status.last_sync_status == "FAILED":
                print(f"[WARN] Sync Failed Reason: {sync_status.last_sync_error}")
        else:
            print("[WARN] No Sync Status found (Sync might be running or failed silently)")

        # 4. Search verification
        print("\n--- Verifying Search Logic ---")
        results = stock_master_service.search_stocks("7203")
        print(f"Search '7203': {results}")
        if any(r['code'] == '7203' for r in results):
             print("[PASS] Search '7203' returned Toyota")
        else:
             print("[FAIL] Search '7203' failed")

        results_name = stock_master_service.search_stocks("ソニー")
        print(f"Search 'ソニー': {results_name}")
        if any(r['code'] == '6758' for r in results_name):
             print("[PASS] Search 'ソニー' returned Sony")
        else:
             print("[FAIL] Search 'ソニー' failed")

    finally:
        db.close()

if __name__ == "__main__":
    verify_stock_master()
