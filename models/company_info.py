
from sqlalchemy import Column, Integer, String, BigInteger, Text, DateTime, ForeignKey, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class Sector(Base):
    __tablename__ = "sectors"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True) # e.g. "Electric Appliances"
    
class Market(Base):
    __tablename__ = "markets"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True) # e.g. "Prime"

class CompanyInfo(Base):
    __tablename__ = "company_info"
    
    id = Column(Integer, primary_key=True, index=True)
    stock_code = Column(String, ForeignKey("stock_master.code"), nullable=False, unique=True)
    edinet_code = Column(String, unique=True, index=True) # E-Code
    
    corporate_name_ja = Column(String, nullable=True)
    corporate_name_en = Column(String, nullable=True)
    
    address = Column(String, nullable=True)
    capital = Column(BigInteger, nullable=True)
    representative = Column(String, nullable=True)
    settlement_date = Column(String, nullable=True) # e.g. "3月31日"
    
    sector_id = Column(Integer, ForeignKey("sectors.id"), nullable=True)
    market_id = Column(Integer, ForeignKey("markets.id"), nullable=True)
    
    founded_date = Column(Date, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    stock_master = relationship("models.master.StockMaster", backref="company_info")
    sector = relationship("Sector")
    market = relationship("Market")

