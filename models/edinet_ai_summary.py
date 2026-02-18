
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, func, JSON, Index
from database import Base

class EdinetAISummary(Base):
    __tablename__ = "edinet_ai_summary"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sec_code = Column(String, nullable=False, index=True)
    period_end_year = Column(Integer, nullable=False)
    kind = Column(String, nullable=False) # SNAPSHOT or DELTA

    summary_text = Column(Text, nullable=True)
    bullet_points = Column(JSON, nullable=True)
    
    evidence = Column(JSON, nullable=False)
    input_hash = Column(String, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_ai_summary_unique", "sec_code", "period_end_year", "kind", unique=True),
    )
