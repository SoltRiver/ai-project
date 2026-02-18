
import sys
import argparse
from sqlalchemy import text

# Add project root
sys.path.insert(0, ".")

from database import SessionLocal

from services.timeseries_processor import TimeseriesProcessor

def process_timeseries_batch(sec_code=None, limit=None):
    db = SessionLocal()
    processor = TimeseriesProcessor(db=db)
    
    try:
        if sec_code:
            sec_codes = [sec_code]
        else:
            # Get distinct sec_codes from documents
            stmt = text("SELECT DISTINCT sec_code FROM edinet_documents WHERE sec_code IS NOT NULL")
            if limit:
                stmt = text(f"SELECT DISTINCT sec_code FROM edinet_documents WHERE sec_code IS NOT NULL LIMIT {limit}")
            
            rows = db.execute(stmt).fetchall()
            sec_codes = [r[0] for r in rows]
            
        print(f"--- Processing Timeseries for {len(sec_codes)} companies ---")
        
        for i, code in enumerate(sec_codes):
            print(f"[{i+1}/{len(sec_codes)}] Processing {code}...")
            processor.process_sec_code(code)
            
        print("--- Batch Complete ---")

    except Exception as e:
        print(f"Batch Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sec_code", type=str, help="Specific SecCode")
    parser.add_argument("--limit", type=int, help="Limit number of companies")
    args = parser.parse_args()
    
    process_timeseries_batch(sec_code=args.sec_code, limit=args.limit)
