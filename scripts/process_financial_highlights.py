import sys
import argparse
import logging
from sqlalchemy.orm import Session
from sqlalchemy import create_engine

# Add project root
sys.path.insert(0, ".")

from database import SessionLocal
from models.edinet_document import EdinetDocument
from services.financial_processor import FinancialProcessor

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Process Financial Highlights.")
    parser.add_argument(
        "--doc_id", type=str, help="Specific DocID to process", default=None
    )
    parser.add_argument(
        "--limit", type=int, help="Limit number of docs to process", default=None
    )

    args = parser.parse_args()

    db = SessionLocal()
    processor = FinancialProcessor(db=db)

    # Select target documents
    # We want docs that have xbrl_flag=1 and preferably have facts in edinet_xbrl_fact
    # But querying distinct doc_id from edinet_xbrl_fact is better.

    if args.doc_id:
        doc_ids = [args.doc_id]
    else:
        # Get distinct doc_ids from facts
        # limit?
        from sqlalchemy import text

        query = text("SELECT DISTINCT doc_id FROM edinet_xbrl_fact")
        if args.limit:
            query = text(
                f"SELECT DISTINCT doc_id FROM edinet_xbrl_fact LIMIT {args.limit}"
            )

        result = db.execute(query)
        doc_ids = [row[0] for row in result]

    print(f"Found {len(doc_ids)} documents to process.")

    for i, doc_id in enumerate(doc_ids):
        print(f"[{i+1}/{len(doc_ids)}] Processing {doc_id}...")
        try:
            processor.process_document(doc_id)
        except Exception as e:
            logger.error(f"Error processing {doc_id}: {e}")

    print("--- Batch Complete ---")
    db.close()


if __name__ == "__main__":
    main()
