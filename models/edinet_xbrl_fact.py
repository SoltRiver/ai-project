
from sqlalchemy import Column, Integer, String, Date, DateTime, Boolean, Text, Numeric, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy import ForeignKey
from database import Base

class EdinetXbrlFact(Base):
    __tablename__ = "edinet_xbrl_fact"

    id = Column(Integer, primary_key=True, index=True) # BigSerial in Postgres
    
    # FK to EdinetDocument
    doc_id = Column(String(8), ForeignKey("edinet_documents.doc_id", ondelete="CASCADE"), nullable=False, index=True)
    
    concept = Column(Text, nullable=False, index=True) # Element Name (e.g. jppfs_cor:NetSales)
    
    value_text = Column(Text, nullable=True)
    value_numeric = Column(Numeric, nullable=True) # Postgres Numeric
    
    unit_ref = Column(Text, nullable=True)
    decimals = Column(Text, nullable=True)
    
    period_start = Column(Date, nullable=True)
    period_end = Column(Date, nullable=True)
    instant_date = Column(Date, nullable=True)
    
    entity_id = Column(Text, nullable=True)
    context_ref = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Constraints for MVP (Postgres Compatible)
    # UNIQUE (doc_id, concept, context_ref, unit_ref, ...) 
    # Note: SQLite has limits on index size/columns, but we try to match Postgres.
    # Coalesce is not directly supported in UniqueConstraint definition in SQLAlchemy Core usually without DDL string.
    # We will rely on application level checks or Index with unique=True if possible.
    # But SQLAlchemy UniqueConstraint doesn't support expressions standardly across all DBs easily.
    # For SQLite, we might skip the complex unique constraint or define it via __table_args__.
    
    # Requirement:
    # UNIQUE (doc_id, concept, context_ref, unit_ref, coalesce(value_text,''), ...)
    # This is a functional index/constraint.
    # For now, we define a standard UniqueConstraint on the key fields if possible, 
    # or just trust the application IDEMPOTENCY logic which deletes/skips before insert.
    # The PROMPT says "DB側の UNIQUE と、可能ならアプリ側の重複排除"
    # We will try to add a simpler UniqueConstraint for now, or just leave it to custom indexes in Postgres DDL.
    # Implementing the exact DDL requested in Postgres via migration script is key.
    
    # We will omit the complex functional UniqueConstraint here to avoid SQLite issues in python.
    # (SQLite doesn't support function-based indexes in UniqueConstraint easily in ORM)
