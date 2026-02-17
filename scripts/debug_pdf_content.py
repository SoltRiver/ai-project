
import sys
# Add project root
sys.path.insert(0, ".")

from sqlalchemy import text
from database import SessionLocal

def debug_pdf_content(doc_id):
    db = SessionLocal()
    try:
        # Check matching pages via SQL
        print(f"--- SQL Search in {doc_id} ---")
        sql_search = text("SELECT page_no, text_body FROM edinet_pdf_text WHERE doc_id=:d AND text_body LIKE :q")
        # SQLite LIKE is case-insensitive for ASCII by default
        rows = db.execute(sql_search, {"d": doc_id, "q": "%Management%"}).fetchall()
        
        print(f"SQL LIKE matches: {len(rows)}")
        for r in rows:
            print(f" - Page {r[0]}")
            body = r[1]
            idx = body.lower().find("management")
            print(f"   Python find 'management': {idx}")
            if idx != -1:
                 print(f"   Context: {body[idx-20:idx+30]}")
            else:
                 print("   [WARNING] SQL matched but Python failed.")
                 print(f"   Excerpt: {body[:100]}...") # Print start
                 
    finally:
        db.close()

if __name__ == "__main__":
    debug_pdf_content("S100TT51")
