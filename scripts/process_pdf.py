
import sys
import argparse
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import create_engine

# Add project root
sys.path.insert(0, ".")

from database import SessionLocal
from services.pdf_processor import PdfProcessor
from models.edinet_document import EdinetDocument
from models.edinet_file import EdinetFile

def process_pdf_batch(limit: int = 10):
    db = SessionLocal()
    processor = PdfProcessor(db=db)
    
    print(f"--- Processing PDF Batch (Limit: {limit}) ---")
    
    try:
        # Find candidates: 
        # 1. Has PDF_TYPE2 (OK) in EdinetFile
        # 2. Not processed YES in EdinetPdfExtractStatus (or status != OK)
        # Note: We can join tables but for simplicity/batching:
        # Get list of doc_ids from EdinetFile where type=PDF_TYPE2 and status=OK
        
        # Efficient query:
        # SELECT f.doc_id FROM edinet_files f
        # LEFT JOIN edinet_pdf_extract_status s ON f.doc_id = s.doc_id
        # WHERE f.file_type = 'PDF_TYPE2' AND f.status = 'OK'
        # AND (s.status IS NULL OR s.status != 'OK')
        # LIMIT :limit
        
        from models.edinet_pdf import EdinetPdfExtractStatus
        
        qt = db.query(EdinetFile.doc_id)\
            .outerjoin(EdinetPdfExtractStatus, EdinetFile.doc_id == EdinetPdfExtractStatus.doc_id)\
            .filter(EdinetFile.file_type == "PDF_TYPE2")\
            .filter(EdinetFile.status == "OK")\
            .filter((EdinetPdfExtractStatus.status == None) | (EdinetPdfExtractStatus.status != "OK"))\
            .limit(limit)
            
        candidates = qt.all()
        doc_ids = [r[0] for r in candidates]
        
        print(f"Found {len(doc_ids)} documents to process.")
        
        success_count = 0
        skip_count = 0
        error_count = 0
        
        for i, doc_id in enumerate(doc_ids):
            print(f"[{i+1}/{len(doc_ids)}] Processing {doc_id}...")
            
            result = processor.process_document(doc_id)
            
            status = result.get("status")
            if status == "OK":
                print(f"  Success: {result.get('page_count')} pages, {result.get('total_chars')} chars")
                success_count += 1
            elif status == "SKIP":
                print(f"  Skipped: {result.get('reason')}")
                skip_count += 1
            else:
                print(f"  Error: {result.get('error_message')}")
                error_count += 1
                
        print(f"--- Batch Complete ---")
        print(f"Success: {success_count}, Skipped: {skip_count}, Errors: {error_count}")
        
    except Exception as e:
        print(f"Batch Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10, help="Number of docs to process")
    args = parser.parse_args()
    
    process_pdf_batch(limit=args.limit)
