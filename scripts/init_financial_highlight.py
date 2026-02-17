
import sys
import os

# Add project root
sys.path.insert(0, ".")

from database import engine
from models.edinet_financial_highlight import EdinetFinancialHighlight
# Import dependencies to ensure FKs work (though create_all handles order usually, imports are safe)
from models.edinet_document import EdinetDocument
from models.edinet_xbrl_fact import EdinetXbrlFact

def init_db():
    print("Initializing EdinetFinancialHighlight table...")
    # Drop first to ensure schema
    EdinetFinancialHighlight.__table__.drop(bind=engine, checkfirst=True)
    EdinetFinancialHighlight.metadata.create_all(bind=engine)
    print("Table 'edinet_financial_highlight' dropped and recreated.")

if __name__ == "__main__":
    init_db()
