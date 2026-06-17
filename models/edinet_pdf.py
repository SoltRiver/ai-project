from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, func, Index
from sqlalchemy.orm import relationship
from database import Base


class EdinetPdfExtractStatus(Base):
    __tablename__ = "edinet_pdf_extract_status"

    doc_id = Column(String(8), ForeignKey("edinet_documents.doc_id"), primary_key=True)
    status = Column(String(10), nullable=False)  # OK, NG, SKIP
    page_count = Column(Integer)
    total_chars = Column(Integer)
    rule_version = Column(String(10), default="v1")
    error_message = Column(Text)
    processed_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class EdinetPdfText(Base):
    __tablename__ = "edinet_pdf_text"

    doc_id = Column(String(8), ForeignKey("edinet_documents.doc_id"), primary_key=True)
    page_no = Column(Integer, primary_key=True)
    text_body = Column(Text)
    text_len = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships if needed
    # document = relationship("EdinetDocument", back_populates="pdf_texts")
