import sys
import os
import time
from datetime import datetime, timedelta
from typing import Optional
from dotenv import load_dotenv

# Load env before other imports if possible, or just before main
load_dotenv()

# Add project root
sys.path.insert(0, ".")

from database import SessionLocal
from models import master, company_info, edinet_file
from models.company_info import CompanyInfo
from models.edinet_file import EdinetFile
from services.edinet_service import EdinetClient
from services.edinet_storage import EdinetStorageService


def parse_settlement_date(s_date: str) -> Optional[tuple]:
    """
    Parse "3月31日" -> (3, 31).
    """
    if not s_date:
        return None
    try:
        s_date = s_date.replace("決算", "").strip()
        parts = s_date.split("月")
        if len(parts) == 2:
            m = int(parts[0])
            d = int(parts[1].replace("日", ""))
            return (m, d)
    except:
        return None
    return None


def fetch_nikkei_documents():
    db = SessionLocal()
    client = EdinetClient()
    # Ensure storage service uses same DB session if possible, or new one.
    # Updated EdinetStorageService uses SessionLocal() inside if not provided,
    # but we can pass db if we updated the init?
    # Checking EdinetStorageService.__init__: def __init__(self, db: Session = None):
    # So we can pass db.
    storage = EdinetStorageService(db=db)

    print("--- Starting Document Fetch (Annual Reports) ---")

    companies = db.query(CompanyInfo).filter(CompanyInfo.edinet_code.isnot(None)).all()
    print(f"Found {len(companies)} companies with Edinet Code.")

    # Target: Latest Annual Securities Report (120)
    # Strategy:
    # 1. Estimate filing window based on settlement date.
    # 2. Check if we already have a 120 doc for this company filed around that time.
    # 3. If not, fetch.

    current_date = datetime.now()  # Mockable? 2026-02-16

    for company in companies:
        name = company.corporate_name_ja
        code = company.stock_code
        e_code = company.edinet_code
        settlement = company.settlement_date

        print(f"Processing {code} {name} (Settlement: {settlement})...")

        md = parse_settlement_date(settlement)
        if not md:
            print(f"  Unknown settlement date format. Skipping smart search.")
            continue

        month, day = md

        # Logic:
        # If settlement is Month M. Filing is M+3.
        # We want the LAST filed report.
        # If Today is 2026-02-16.
        # If settlement is 3/31. Last settlement was 2025-03-31. Filing ~June 2025.
        # If settlement is 12/31. Last settlement was 2025-12-31. Filing ~March 2026 (Not yet/Available?).
        #    Or 2024-12-31. Filing March 2025.

        # Simple heuristic: Look at the Primary Filing Month for the *Previous* Year (2025)?
        # Since logic might be complex, we define a "Target Search Window".
        # For Mar-31 companies (most): June 2025.
        # For Feb-28 companies (Retail): May 2025.

        # Let's assume prediction: Year = 2025.
        search_year = 2025

        # Special logic to find "Latest".
        # We can search backwards from Today?
        # But scanning 365 days is slow.
        # Let's target the specifc "Filing Month" of 2025.

        filing_month = month + 3
        filing_year = search_year
        if filing_month > 12:
            filing_month -= 12
            filing_year += 1

        print(f"  Targeting Filing Month: {filing_year}-{filing_month}")

        # Scan the whole month? Or just specific days?
        # Filings cluster at end of month usually. June 20-30.
        # Let's scan last 15 days of that month?

        import calendar

        last_day = calendar.monthrange(filing_year, filing_month)[1]

        start_date = datetime(filing_year, filing_month, last_day)  # End of month

        found_doc = None
        SCAN_DAYS = 20

        for i in range(SCAN_DAYS):
            target_date = start_date - timedelta(days=i)
            # print(f"  Scanning {target_date.strftime('%Y-%m-%d')}...")

            docs = client.get_documents_by_date(target_date, type_code=1)

            # Filter for this company and Type 120
            for doc in docs:
                if doc.get("edinetCode") == e_code and doc.get("docTypeCode") == "120":
                    found_doc = doc
                    break

            if found_doc:
                break

        if found_doc:
            doc_id = found_doc.get("docID")
            submitter_name = found_doc.get("submitterName")
            period_end_str = found_doc.get("periodEnd")  # YYYY-MM-DD
            print(
                f"  FOUND Document: {doc_id} / {submitter_name} / PeriodEnd: {period_end_str}"
            )

            # Check DB
            existing = storage.get_file_record(doc_id, "ZIP_TYPE1")

            if existing and existing.status == "OK":
                print(f"  Already downloaded. Path: {existing.storage_path}")
                # Update metadata if missing?
                if not existing.period_end and period_end_str:
                    existing.period_end = datetime.strptime(
                        period_end_str, "%Y-%m-%d"
                    ).date()
                    existing.submitter_code = e_code
                    existing.doc_type_code = "120"
                    db.commit()
                    print("  Updated missing metadata in DB.")
            else:
                # Download
                print(f"  Downloading content for {doc_id}...")
                content = client.fetch_document_content_zip(doc_id)
                if content:
                    # Save
                    date_obj = target_date  # Use filing date for folder structure

                    # Parse period_end
                    p_end = None
                    if period_end_str:
                        try:
                            p_end = datetime.strptime(period_end_str, "%Y-%m-%d").date()
                        except:
                            pass

                    saved_file = storage.save_raw_file(
                        doc_id=doc_id,
                        date_obj=date_obj,
                        file_type="ZIP_TYPE1",
                        content=content,
                        submitter_code=e_code,
                        doc_type_code="120",
                        period_end=p_end,
                    )
                    print(f"  Saved to {saved_file.storage_path}")
                else:
                    print(f"  Failed to download content.")

        else:
            print(
                f"  No Annual Report (120) found in scan window ({start_date.strftime('%Y-%m-%d')} - {SCAN_DAYS} days back)."
            )

        # Sleep to be nice to API
        time.sleep(1)

    db.close()
    print("--- Fetch Complete ---")


if __name__ == "__main__":
    fetch_nikkei_documents()
