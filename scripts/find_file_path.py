import sys

# Add project root
sys.path.insert(0, ".")

from sqlalchemy import text
from database import SessionLocal


def find_path(doc_id):
    db = SessionLocal()
    try:
        r = db.execute(
            text(
                "SELECT storage_path FROM edinet_files WHERE doc_id=:d AND file_type='ZIP_TYPE1'"
            ),
            {"d": doc_id},
        ).fetchone()
        if r:
            print(f"Path: {r[0]}")
        else:
            print("Not found")
    finally:
        db.close()


if __name__ == "__main__":
    find_path("S100TSFF")
