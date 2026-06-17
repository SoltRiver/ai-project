import sys
import argparse
from sqlalchemy import text

# Add project root
sys.path.insert(0, ".")

from database import SessionLocal


def verify_timeseries():
    db = SessionLocal()
    print("--- Verifying Timeseries & Comparison ---")

    try:
        # 1. Timeseries Count
        ts_count = db.execute(
            text("SELECT count(*) FROM edinet_metric_timeseries")
        ).scalar()
        print(f"Timeseries Records: {ts_count}")

        if ts_count == 0:
            print("[WARN] No timeseries data. Did you run process_timeseries.py?")
            return

        # 2. Comparison Count
        comp_count = db.execute(
            text("SELECT count(*) FROM edinet_metric_comparison")
        ).scalar()
        print(f"Comparison Records: {comp_count}")

        # 3. Check YoY Logic (Sample)
        print("\n[Sample: YoY Calculation]")
        rows = db.execute(text("""
            SELECT sec_code, metric_key, period_end_year, yoy_pct, turnaround_flag
            FROM edinet_metric_comparison
            WHERE yoy_pct IS NOT NULL OR turnaround_flag IS NOT NULL
            LIMIT 5
        """)).fetchall()

        for r in rows:
            print(f"Sec: {r[0]}, Metric: {r[1]}, Year: {r[2]}")
            print(f"  YoY: {r[3]}, Turnaround: {r[4]}")

        # 4. Check Unique Constraint (Safety)
        print("\n[Safety Check: Duplicates]")
        dupes = db.execute(text("""
            SELECT sec_code, metric_key, period_end_year, count(*)
            FROM edinet_metric_timeseries
            GROUP BY sec_code, metric_key, period_end_year
            HAVING count(*) > 1
        """)).fetchall()

        if dupes:
            print(f"[FAIL] Found duplicates: {dupes}")
        else:
            print("[PASS] No duplicates found.")

    finally:
        db.close()


if __name__ == "__main__":
    verify_timeseries()
