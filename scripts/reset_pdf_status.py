
import sys
# Add project root
sys.path.insert(0, ".")

from database import SessionLocal
from models.edinet_pdf import EdinetPdfExtractStatus

def reset_pdf_status():
    db = SessionLocal()
    print("Resetting PDF Extract Status...")
    try:
        # Delete all records or specific ones?
        # For now, delete ALL to facilitate re-processing of the batch
        count = db.query(EdinetPdfExtractStatus).delete()
        db.commit()
        print(f"Deleted {count} records from EdinetPdfExtractStatus.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    reset_pdf_status()
