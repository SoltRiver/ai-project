
import sys
import logging
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add project root
sys.path.insert(0, ".")

from database import DATABASE_URL, Base
from models.stock_impact import StockNews, StockNewsAnalysis, StockEvent, StockEventAnalysis
from services.impact_bias_service import ImpactBiasService

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_impact_bias():
    # Setup DB
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # helper to recreate tables for test
    logger.info("Recreating Impact Tables...")
    StockNewsAnalysis.__table__.drop(engine, checkfirst=True)
    StockNews.__table__.drop(engine, checkfirst=True)
    StockEventAnalysis.__table__.drop(engine, checkfirst=True)
    StockEvent.__table__.drop(engine, checkfirst=True)
    
    Base.metadata.create_all(engine)
    
    # Data Injection
    sec_code = "9999"
    now = datetime.now()
    
    # 1. News (3 POS, 2 NEG, 1 NEUTRAL)
    news_data = [
        ("N1", "Positive News 1 High", "POS", "HIGH"),
        ("N2", "Positive News 2 Med", "POS", "MEDIUM"),
        ("N3", "Positive News 3 Low", "POS", "LOW"),
        ("N4", "Negative News 1 High", "NEG", "HIGH"),
        ("N5", "Negative News 2 Med", "NEG", "MEDIUM"),
        ("N6", "Neutral News 1", "NEUTRAL", "LOW"),
    ]
    
    for i, (title, summary, im_type, strength) in enumerate(news_data):
        n = StockNews(
            sec_code=sec_code,
            source_name="Test Source",
            title=title,
            published_at=now - timedelta(days=i)
        )
        session.add(n)
        session.flush()
        
        # Map
        itype = "POSITIVE" if im_type == "POS" else "NEGATIVE" if im_type == "NEG" else "NEUTRAL"
        
        na = StockNewsAnalysis(
            news_id=n.id,
            impact_type=itype,
            impact_strength=strength,
            summary_2lines=summary
        )
        session.add(na)

    # 2. Events (2 POS, 1 NEG)
    event_data = [
        ("E1", "Event Pos High", "POS", "HIGH"),
        ("E2", "Event Pos Med", "POS", "MEDIUM"),
        ("E3", "Event Neg High", "NEG", "HIGH"),
    ]
    
    for i, (title, summary, im_type, strength) in enumerate(event_data):
        e = StockEvent(
            sec_code=sec_code,
            event_type="Disclosure",
            title=title,
            announced_at=now - timedelta(days=i)
        )
        session.add(e)
        session.flush()
        
        itype = "POSITIVE" if im_type == "POS" else "NEGATIVE"
        
        ea = StockEventAnalysis(
            event_id=e.id,
            impact_type=itype,
            impact_strength=strength,
            summary_2lines=summary
        )
        session.add(ea)
        
    session.commit()
    
    # 3. Verify Service
    service = ImpactBiasService(session)
    result = service.get_impact_bias(sec_code)
    
    print("\n--- Result ---")
    print(f"Total: {result['meta']['total_count']} (Expect 8)")
    print(f"POS Ratio: {result['stats']['pos_ratio_pct']}% (Expect 62.5%)")
    print(f"NEG Ratio: {result['stats']['neg_ratio_pct']}% (Expect 37.5%)")
    
    print("\n[Positive Items]")
    for item in result['items']['positive']:
        print(f" - {item['strength']} {item['type']}: {item['title']}")
        
    print("\n[Negative Items]")
    for item in result['items']['negative']:
        print(f" - {item['strength']} {item['type']}: {item['title']}")
        
    # Assertions
    assert result['meta']['total_count'] == 8
    assert result['stats']['pos_ratio_pct'] == 62.5
    assert result['stats']['neg_ratio_pct'] == 37.5
    
    # Sort check: High strength should be first
    first_pos = result['items']['positive'][0]
    assert first_pos['strength'] == "HIGH"
    
    print("\n[PASS] Impact Bias Verification Successful.")
    session.close()

if __name__ == "__main__":
    verify_impact_bias()
