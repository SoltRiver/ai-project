import sys
import argparse
from sqlalchemy import text

# Add project root
sys.path.insert(0, ".")

from database import SessionLocal


def verify_derived():
    db = SessionLocal()
    print("--- Verifying Derived Metrics ---")

    try:
        # 1. Count
        count = db.execute(
            text("SELECT count(*) FROM edinet_financial_derived")
        ).scalar()
        print(f"Total Derived Metrics: {count}")

        # 2. Sample Check (Operating Margin)
        print("\n[Sample: Operating Margin]")
        rows = db.execute(text("""
            SELECT doc_id, value_numeric, confidence, reason, source_values
            FROM edinet_financial_derived 
            WHERE derived_key = 'operating_margin' 
            AND value_numeric IS NOT NULL
            LIMIT 3
        """)).fetchall()

        for r in rows:
            print(f"Doc: {r[0]}, Val: {r[1]}, Conf: {r[2]}")
            print(f"Reason: {r[3]}")
            # Simplified JSON view
            # In SQLite, JSON is text, might need parsing if we want to deep check.
            # But just printing is enough for visual verify.
            # print(f"Source: {r[4]}")

        # 3. Sample Check (ROE Mixed)
        print("\n[Sample: ROE (Mixed Approx)]")
        rows = db.execute(text("""
            SELECT doc_id, value_numeric, period_type, duration_days
            FROM edinet_financial_derived 
            WHERE derived_key = 'roe_end' 
            AND value_numeric IS NOT NULL
            LIMIT 3
        """)).fetchall()

        for r in rows:
            print(f"Doc: {r[0]}, Val: {r[1]}, Period: {r[2]}, Days: {r[3]}")

        if count == 0:
            print("\n[WARN] No metrics found. Did you run process_derived_metrics.py?")

    finally:
        db.close()


if __name__ == "__main__":
    verify_derived()
