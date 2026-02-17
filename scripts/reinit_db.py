
import sys
import os
from sqlalchemy import text

# Add project root
sys.path.insert(0, ".")

from database import SessionLocal, engine
from models import company_info, edinet_file

def reinit_db():
    print("WARNING: This will DROP 'company_info', 'sectors', 'markets', 'edinet_files' tables.")
    # In dev, we can drop everything relevant
    
    # We use raw sql or metadata
    # But metadata.drop_all might drop everything if we imported everything?
    # Let's drop specific tables to be safe (not stock_master if we want to keep it? 
    # Actually integrate_nikkei_225 upserts stock_master too. So it's safe to drop.)
    
    try:
        # Drop strictly related tables
        company_info.Base.metadata.drop_all(bind=engine) # This handles CompanyInfo, Sector, Market
        edinet_file.Base.metadata.drop_all(bind=engine) # This handles EdinetFile
        print("Dropped tables.")
    except Exception as e:
        print(f"Error dropping tables: {e}")

    try:
        # Recreate
        company_info.Base.metadata.create_all(bind=engine)
        edinet_file.Base.metadata.create_all(bind=engine)
        print("Recreated tables with new schema.")
    except Exception as e:
        print(f"Error creating tables: {e}")

if __name__ == "__main__":
    reinit_db()
