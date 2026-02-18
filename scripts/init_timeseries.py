
import sys
# Add project root
sys.path.insert(0, ".")

from sqlalchemy import create_engine
from database import Base, engine
from models.edinet_document import EdinetDocument
from models.edinet_timeseries import EdinetMetricTimeseries, EdinetMetricComparison

def init_timeseries_tables():
    print("Initializing Edinet Timeseries Tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created (if not exists).")

if __name__ == "__main__":
    init_timeseries_tables()
