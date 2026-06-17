import sys
import argparse
from datetime import datetime, timedelta

# Add project root
sys.path.insert(0, ".")

from services.search_service import SearchService
from database import SessionLocal


def verify_search():
    db = SessionLocal()
    searcher = SearchService(db=db)

    print("\n--- 1. Query Guard Tests ---")

    # Too short
    res = searcher.search("A")
    print(f"Query 'A': {res.get('status')} - {res.get('message')}")

    # 2 chars without filter
    res = searcher.search("AI")
    print(f"Query 'AI' (no filter): {res.get('status')} - {res.get('message')}")

    # 2 chars with filter
    res = searcher.search("AI", date_from=datetime(2024, 1, 1))
    print(
        f"Query 'AI' (with date): {res.get('status')} (Expected OK/ERROR depending on DB content)"
    )

    print("\n--- 2. Normal Search Tests ---")

    # Valid query
    # "経営方針" is common in Annual Reports
    q = "経営方針"
    res = searcher.search(q, limit=5)
    print(f"Query '{q}': Found {res.get('count')} docs")
    if res.get("status") == "OK":
        for r in res.get("results"):
            print(f" - [{r['doc_id']}] Page {r['page_no']}: {r['snippet']}")

    print("\n--- 3. Japanese Snippet Test ---")
    q_jp = "経営方針"
    res = searcher.search(q_jp, limit=2)
    print(f"Query '{q_jp}': Found {res.get('count')}")
    for r in res.get("results"):
        print(f" - [{r['doc_id']}] Page {r['page_no']}: {r['snippet']}")

    db.close()


if __name__ == "__main__":
    verify_search()
