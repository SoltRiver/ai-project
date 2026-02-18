import sys
import json
from sqlalchemy import text

# Add project root
sys.path.insert(0, ".")


from database import SessionLocal

def verify_ai_summary():
    db = SessionLocal()
    print("--- Verifying AI Summary ---")
    
    try:
        # 1. Count
        count = db.execute(text("SELECT count(*) FROM edinet_ai_summary")).scalar()
        print(f"Total Summaries: {count}")
        
        if count == 0:
            print("[WARN] No summaries found. Did you run process_ai_summary.py?")
            return

        # 2. Integrity Check (Text matches Evidence)
        print("\n[Sample Check]")
        rows = db.execute(text("""
            SELECT sec_code, period_end_year, kind, summary_text, evidence
            FROM edinet_ai_summary
            LIMIT 6
        """)).fetchall()
        
        for r in rows:
            sec = r[0]
            year = r[1]
            kind = r[2]
            txt = r[3]
            ev = r[4] # SQLAlchemy handles JSON deserialization for JSON type columns usually, but let's see. 
            # In SQLite with JSON stored as text, we might need json.loads. 
            # In Postgres with JSONB, it is returned as dict.
            # Using SessionLocal (SQLAlchemy), existing code used db.execute(text). 
            # If using psycopg2 driver, it returns dict. If sqlite, string.
            # To be safe:
            if isinstance(ev, str):
                ev = json.loads(ev)
            
            print(f"[{sec} {year} {kind}]")
            # print(f"Text snippet: {txt[:30]}...")
            
            if kind == "SNAPSHOT":
                sales_disp = ev.get("snapshot", {}).get("net_sales", {}).get("display")
                if sales_disp and sales_disp != "-" and sales_disp not in txt:
                    print(f"[FAIL] Sales {sales_disp} not found in text!")
                else:
                    print(f"[PASS] Snapshot check OK ({sales_disp})")
                    
            if kind == "DELTA":
                # Check if percentage exists
                s_delta = ev.get("delta", {}).get("net_sales", {})
                yoy_pct = s_delta.get("yoy_pct")
                
                if yoy_pct and yoy_pct != "null":
                    val = float(yoy_pct) * 100
                    expected = f"{val:.1f}%"
                    if expected not in txt:
                         # It might be "turnaround" text?
                         turnaround = s_delta.get("turnaround")
                         if turnaround and turnaround in txt:
                             print(f"[PASS] Delta check OK (Turnaround: {turnaround})")
                         else:
                             print(f"[FAIL] Delta {expected} not found in text! (Turnaround: {turnaround})")
                    else:
                        print(f"[PASS] Delta check OK ({expected})")
                else:
                    print("[PASS] Delta check OK (No Sales Delta)")

    finally:
        db.close()

if __name__ == "__main__":
    verify_ai_summary()
