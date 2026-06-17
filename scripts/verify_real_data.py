import sys
from sqlalchemy import text
from sqlalchemy.orm import Session
import argparse

# Add project root
sys.path.insert(0, ".")

from database import SessionLocal


def verify(target_date):
    db = SessionLocal()
    print(f"--- Verification Report for {target_date} ---")

    try:
        # Total Counts
        t_docs = db.execute(text("SELECT COUNT(*) FROM edinet_documents")).scalar()
        t_files = db.execute(text("SELECT COUNT(*) FROM edinet_files")).scalar()
        t_facts = db.execute(text("SELECT COUNT(*) FROM edinet_xbrl_fact")).scalar()
        print(f"TOTAL: Docs={t_docs}, Files={t_files}, Facts={t_facts}")

        # 1. Edinet Files
        q1 = text("""
            SELECT COUNT(*) FROM edinet_files f
            JOIN edinet_documents d ON f.doc_id = d.doc_id
            WHERE d.target_date = :date
        """)
        file_count = db.execute(q1, {"date": target_date}).scalar()
        print(f"EdinetFiles (Downloaded): {file_count}")

        # 2. Facts
        q2 = text("""
            SELECT COUNT(*) FROM edinet_xbrl_fact x
            JOIN edinet_documents d ON x.doc_id = d.doc_id
            WHERE d.target_date = :date
        """)
        fact_count = db.execute(q2, {"date": target_date}).scalar()
        print(f"XBRL Facts (Extracted): {fact_count}")

        # 3. Highlights
        q3 = text("""
            SELECT COUNT(*) FROM edinet_financial_highlight h
            JOIN edinet_documents d ON h.doc_id = d.doc_id
            WHERE d.target_date = :date
        """)
        hl_count = db.execute(q3, {"date": target_date}).scalar()
        print(f"Financial Highlights (Mapped): {hl_count}")

        # 4. Sample
        if hl_count > 0:
            print("\n--- Sample Highlights ---")
            q4 = text("""
                SELECT h.doc_id, h.metric_label, h.metric_key, h.value_numeric, h.unit_label, h.confidence
                FROM edinet_financial_highlight h
                JOIN edinet_documents d ON h.doc_id = d.doc_id
                WHERE d.target_date = :date
                ORDER BY h.value_numeric DESC
                LIMIT 10
            """)
            samples = db.execute(q4, {"date": target_date}).fetchall()
            for s in samples:
                # s is tuple-like
                print(f"[{s[0]}] {s[1]} ({s[2]}): {s[3]:,} ({s[4]}) Conf:{s[5]}")
    except Exception as e:
        print(f"Verification Error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    verify("2024-06-26")
