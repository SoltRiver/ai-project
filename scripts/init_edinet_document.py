
import sys
import os

# Add project root
sys.path.insert(0, ".")

from database import engine
from models.edinet_document import EdinetDocument

def init_db():
    print("Initializing EdinetDocument table...")
    EdinetDocument.metadata.create_all(bind=engine)
    print("Table 'edinet_documents' created (if not exists).")

if __name__ == "__main__":
    init_db()
