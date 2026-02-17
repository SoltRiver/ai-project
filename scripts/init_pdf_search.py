
import sys
import os

# Add project root
sys.path.insert(0, ".")

from sqlalchemy import create_engine, text
from database import Base, engine
from models.edinet_document import EdinetDocument # Required for FK
from models.edinet_pdf import EdinetPdfText, EdinetPdfExtractStatus

def init_pdf_search_tables():
    print("Initializing PDF Search Tables...")
    # Create tables using SQLAlchemy metadata
    # This works for the basic structure.
    Base.metadata.create_all(bind=engine)
    print("Tables created (if not exist).")

    # Create Indexes (Raw SQL for specific types)
    # Phase 6: Hybrid Search
    # We enable TRGM extension and indexes if PostgreSQL.
    # Check if Postgres
    is_postgres = "postgresql" in engine.url.drivername
    
    if is_postgres:
        print("Detected PostgreSQL. Applying optimized indexes...")
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gin;"))
            
            # Text Search Index (TRGM) - Created manually after load usually, but we can init here.
            # User said: "初回大量投入時はインデックス未作成... ロード後に CREATE INDEX"
            # So we might skip heavy indexes here or just create IF NOT EXISTS.
            # Let's create metadata indexes at least.
            
            # idx_pdf_text_doc_id is created via model ? No, via DDL or explicit Index.
            # We defined Index in SQL but not fully in Model (commented out).
            # The model has primary key which creates index.
            
            # Let's run the SQL file content for completeness?
            # Or just rely on SQLAlchemy.
            pass
    else:
        print("Not using PostgreSQL. Skipping PG-specific indexes.")

if __name__ == "__main__":
    init_pdf_search_tables()
