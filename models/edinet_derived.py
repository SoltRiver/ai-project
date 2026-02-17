
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, func, Numeric, Index, JSON
from sqlalchemy.orm import relationship
from database import Base

class EdinetFinancialDerived(Base):
    __tablename__ = "edinet_financial_derived"

    id = Column(Integer, primary_key=True, autoincrement=True)
    doc_id = Column(String(8), ForeignKey("edinet_documents.doc_id", ondelete="CASCADE"), nullable=False)

    derived_key = Column(String, nullable=False)
    derived_label = Column(String, nullable=False)

    value_numeric = Column(Numeric, nullable=True) # Check if SQLite supports Numeric properly (it treats as Real/Text)

    period_type = Column(String, nullable=True)
    duration_days = Column(Integer, nullable=True)

    # JSON types for source tracking
    # SQLite requires dialect specific or strict JSON type handling if using standard JSON
    # SQLAlchemy's JSON type works on SQLite (as JSON string) and Postgres (as JSON/JSONB)
    source_metrics = Column(JSON, nullable=False)
    source_values = Column(JSON, nullable=False)
    calculation_formula = Column(Text, nullable=False)

    confidence = Column(String, nullable=True) # HIGH/MID/LOW
    reason = Column(Text, nullable=True)

    variant_key = Column(String, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Unique constraint via Index is standard in SQLA, but UNIQUE constraint is better defined in __table_args__
    # UNIQUE (doc_id, derived_key)
    __table_args__ = (
        Index("idx_derived_unique", "doc_id", "derived_key", unique=True),
    )
    
    # Relationships
    # document = relationship("EdinetDocument", back_populates="derived_metrics")
