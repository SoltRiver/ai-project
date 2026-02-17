
from sqlalchemy import Column, Integer, String, Date, DateTime, Numeric, BigInteger, UniqueConstraint, Text
from sqlalchemy.sql import func
from sqlalchemy import ForeignKey
from database import Base

class EdinetFinancialHighlight(Base):
    __tablename__ = "edinet_financial_highlight"

    # Use Integer for SQLite auto-increment compatibility. 
    # Postgres BigSerial is also fine with Integer usually, or use distinct type compilation.
    id = Column(Integer, primary_key=True, index=True) 

    doc_id = Column(String, ForeignKey("edinet_documents.doc_id", ondelete="CASCADE"), nullable=False, index=True)
    
    metric_key = Column(Text, nullable=False, index=True)
    metric_label = Column(Text, nullable=True) # Debugging NOT NULL issue
    
    selected_fact_id = Column(BigInteger, ForeignKey("edinet_xbrl_fact.id"), nullable=True)
    
    scope = Column(Text, default="unknown") # consolidated/non_consolidated/unknown
    period_type = Column(Text, default="unknown") # duration/instant/unknown
    duration_days = Column(Integer, nullable=True)
    
    period_start = Column(Date, nullable=True)
    period_end = Column(Date, nullable=True)
    
    value_numeric = Column(Numeric, nullable=True)
    raw_value_text = Column(Text, nullable=True) # Required
    unit_label = Column(Text, nullable=True)
    source_concept = Column(Text, nullable=True)
    
    confidence = Column(Text, nullable=True) # HIGH/MID/LOW
    reason = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Unique Constraint (Relaxed)
    __table_args__ = (
        UniqueConstraint('doc_id', 'metric_key', name='uq_financial_highlight_doc_metric'),
    )

    def __repr__(self):
        return f"<Highlight(doc={self.doc_id}, key={self.metric_key}, val={self.value_numeric})>"
