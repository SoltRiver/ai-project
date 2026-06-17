import sys
import os

# Add project root
sys.path.insert(0, ".")

from database import engine
from models.edinet_document import EdinetDocument
from models.edinet_xbrl_fact import EdinetXbrlFact


def init_db():
    print("Initializing EdinetXbrlFact table...")
    # Import all models to ensure metadata is populated if needed
    EdinetXbrlFact.metadata.create_all(bind=engine)
    print("Table 'edinet_xbrl_fact' created (if not exists).")


if __name__ == "__main__":
    init_db()
