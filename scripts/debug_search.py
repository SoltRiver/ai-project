import sys

# Add project root
sys.path.insert(0, ".")

from services.search_service import SearchService, TextNormalizer
from database import SessionLocal


def debug_search_service():
    db = SessionLocal()
    searcher = SearchService(db=db)

    query = "Management"
    norm_query = TextNormalizer.normalize_text(query)
    print(f"Original Query: '{query}'")
    print(f"Normalized Query: '{norm_query}'")

    res = searcher.search(query, limit=5)
    print(f"Count: {res.get('count')}")

    for r in res.get("results"):
        print(f"[{r['doc_id']}] Page {r['page_no']}")
        print(f"Snippet: {r['snippet']}")

    db.close()


if __name__ == "__main__":
    debug_search_service()
