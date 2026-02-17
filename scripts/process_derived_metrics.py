
import sys
# Add project root
sys.path.insert(0, ".")

import argparse
from sqlalchemy import text
from database import SessionLocal

from services.derived_metric_processor import DerivedMetricProcessor
from models.edinet_financial_highlight import EdinetFinancialHighlight

def process_derived_batch(doc_id=None, limit=None):
    db = SessionLocal()
    processor = DerivedMetricProcessor(db=db)
    
    try:
        if doc_id:
            doc_ids = [doc_id]
        else:
            # Get docs that have highlights
            # Distinct doc_id from highlights
            stmt = text("SELECT DISTINCT doc_id FROM edinet_financial_highlight")
            if limit:
                stmt = text(f"SELECT DISTINCT doc_id FROM edinet_financial_highlight LIMIT {limit}")
            
            rows = db.execute(stmt).fetchall()
            doc_ids = [r[0] for r in rows]
            
        print(f"--- Processing Derived Metrics for {len(doc_ids)} docs ---")
        
        for i, did in enumerate(doc_ids):
            print(f"[{i+1}/{len(doc_ids)}] Processing {did}...")
            processor.process_document(did)
            
        print("--- Batch Complete ---")

    except Exception as e:
        print(f"Batch Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--doc_id", type=str, help="Specific DocID")
    parser.add_argument("--limit", type=int, help="Limit number of docs")
    args = parser.parse_args()
    
    process_derived_batch(doc_id=args.doc_id, limit=args.limit)
