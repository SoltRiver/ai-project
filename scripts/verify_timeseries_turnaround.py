import sys

# Add project root
sys.path.insert(0, ".")

from sqlalchemy import text
from database import SessionLocal
from services.timeseries_processor import TimeseriesProcessor
from models.edinet_timeseries import EdinetMetricTimeseries


def verify_turnaround():
    db = SessionLocal()
    processor = TimeseriesProcessor(db=db)

    try:
        # 1. Find a candidate with 2024 data
        row = db.execute(text("""
            SELECT sec_code, period_end_year, value_numeric, doc_id
            FROM edinet_metric_timeseries 
            WHERE metric_key = 'operating_profit' AND value_numeric > 0
            LIMIT 1
        """)).fetchone()

        if not row:
            print("No valid operating_profit candidate found to test turnaround.")
            return

        sec_code = row[0]
        curr_year = row[1]
        curr_val = row[2]
        doc_id = row[3]

        print(f"Testing Turnaround for {sec_code} (Year {curr_year}, Val {curr_val})")

        # 2. Insert Mock Previous Year (Negative)
        prev_year = curr_year - 1
        prev_val = -1000000  # Mock Loss

        print(f"Injecting Mock {prev_year} Data: {prev_val}")

        # Manually insert into timeseries
        # Note: We need a dummy doc_id for the FK. safely reuse the same doc_id for this test or need a mock one.
        # Ideally we reuse the same doc_id but logically it's weird. But for FK satisfaction it's fine if doc exists.

        params = {
            "s": sec_code,
            "m": "operating_profit",
            "y": prev_year,
            "l": str(prev_year),
            "d": doc_id,
            "v": prev_val,
            "p": "duration",
            "sel": '{"mock": true}',
        }

        db.execute(
            text("""
            INSERT INTO edinet_metric_timeseries 
            (sec_code, metric_key, period_end_year, fiscal_year_label, doc_id, value_numeric, period_type, selection_notes)
            VALUES (:s, :m, :y, :l, :d, :v, :p, :sel)
            ON CONFLICT (sec_code, metric_key, period_end_year) 
            DO UPDATE SET value_numeric = :v
        """),
            params,
        )
        db.commit()

        # 3. Re-Calculate Comparison
        print("Re-calculating comparisons...")
        processor._calculate_comparisons(sec_code)

        # 4. Check Result
        res = db.execute(
            text("""
            SELECT yoy_abs, yoy_pct, turnaround_flag
            FROM edinet_metric_comparison
            WHERE sec_code = :s AND metric_key = 'operating_profit' AND period_end_year = :y
        """),
            {"s": sec_code, "y": curr_year},
        ).fetchone()

        print("\n--- Result ---")
        print(f"YoY Abs: {res[0]}")
        print(f"YoY Pct: {res[1]} (Should be None for turnaround)")
        print(f"Turnaround: {res[2]} (Expect NEG_TO_POS)")

        if res[2] == "NEG_TO_POS":
            print("[PASS] Turnaround detected.")
        else:
            print("[FAIL] Turnaround NOT detected.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    verify_turnaround()
