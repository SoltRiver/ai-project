import sys
from sqlalchemy.orm import Session
from sqlalchemy import create_engine

# Add project root
sys.path.insert(0, ".")

from database import engine
from models.edinet_file import EdinetFile


def init_db():
    print("Initializing EdinetFile table...")
    EdinetFile.metadata.create_all(bind=engine)
    print("Table 'edinet_files' created (if not exists).")


if __name__ == "__main__":
    init_db()
