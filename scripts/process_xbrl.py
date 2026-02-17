
import sys
import argparse
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root
sys.path.insert(0, ".")

from database import SessionLocal
from models.edinet_file import EdinetFile
from services.xbrl_processor import XbrlProcessor

def main():
    parser = argparse.ArgumentParser(description="Process XBRL files.")
    parser.add_argument("--doc_id", type=str, help="Specific DocID to process", default=None)
    parser.add_argument("--limit", type=int, help="Limit number of docs to process", default=None)
    parser.add_argument("--force", action="store_true", help="Force re-processing (ignore json log)")
    
    args = parser.parse_args()
    
    db = SessionLocal()
    processor = XbrlProcessor(db=db)
    
    query = db.query(EdinetFile).filter_by(file_type="ZIP_TYPE1", status="OK")
    
    if args.doc_id:
        query = query.filter_by(doc_id=args.doc_id)
    
    # Order by downloaded_at desc to process new ones first? Or old ones?
    # New ones might be more relevant.
    query = query.order_by(EdinetFile.downloaded_at.desc())
    
    if args.limit:
        query = query.limit(args.limit)
        
    files = query.all()
    print(f"Found {len(files)} ZIP files to process.")
    
    success_count = 0
    skip_count = 0
    error_count = 0
    
    for i, file_rec in enumerate(files):
        print(f"[{i+1}/{len(files)}] Processing {file_rec.doc_id}...")
        
        # If force, maybe delete json first? 
        # Processor checks json existence.
        # We can implement force logic in processor or here.
        # MVP: simple processor call.
        
        try:
            result = processor.process_document(file_rec.doc_id)
            status = result.get("status")
            if status == "OK":
                success_count += 1
            elif status == "SKIP":
                skip_count += 1
            else:
                error_count += 1
                
        except Exception as e:
            print(f"Critical Error processing {file_rec.doc_id}: {e}")
            error_count += 1
            
        # time.sleep(0.1) # Yield slightly
        
    print(f"--- Batch Complete ---")
    print(f"Success: {success_count}, Skipped: {skip_count}, Errors: {error_count}")
    
    db.close()

if __name__ == "__main__":
    main()
