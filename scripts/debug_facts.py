
import sys
from sqlalchemy import text
from sqlalchemy.orm import Session
import argparse

# Add project root
sys.path.insert(0, ".")

from database import SessionLocal

def debug_facts():
    db = SessionLocal()
    print(f"--- Debug Facts ---")
    
    try:
        q = text("""
            SELECT doc_id, concept, value_numeric, value_text, unit_ref, context_ref
            FROM edinet_xbrl_fact
            LIMIT 20
        """)
        rows = db.execute(q).fetchall()
        for r in rows:
            print(r)
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    debug_facts()
