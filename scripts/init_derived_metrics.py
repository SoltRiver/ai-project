
import sys
# Add project root
sys.path.insert(0, ".")

from sqlalchemy import create_engine
from database import Base, engine
from models.edinet_document import EdinetDocument
from models.edinet_derived import EdinetFinancialDerived

def init_derived_tables():
    print("Initializing EdinetFinancialDerived Table...")
    Base.metadata.create_all(bind=engine)
    print("Table created (if not exists).")

if __name__ == "__main__":
    init_derived_tables()
