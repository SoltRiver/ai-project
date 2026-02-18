
import sys
# Add project root
sys.path.insert(0, ".")

from sqlalchemy import create_engine
from database import Base, engine
from models.edinet_ai_summary import EdinetAISummary
# Import other models to ensure FKs work if needed, though Summary has no FKs strictly enforced in validation?
# It links to sec_code logically.

def init_ai_summary_table():
    print("Initializing Edinet AI Summary Table...")
    Base.metadata.create_all(bind=engine)
    print("Table created (if not exists).")

if __name__ == "__main__":
    init_ai_summary_table()
