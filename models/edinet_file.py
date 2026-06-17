from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    BigInteger,
    UniqueConstraint,
    Date,
)
from sqlalchemy.sql import func
from database import Base


class EdinetFile(Base):
    __tablename__ = "edinet_files"

    id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(String, index=True, nullable=False)
    file_type = Column(String, nullable=False)  # ZIP_TYPE1, PDF_TYPE2, etc.
    storage_path = Column(String, nullable=False)  # Relative path from BASE_STORAGE_DIR
    file_size = Column(BigInteger, nullable=False)
    sha256 = Column(String(64), nullable=False)

    # Metadata for search (Phase 2)
    submitter_code = Column(String, index=True, nullable=True)  # Edinet Code
    doc_type_code = Column(String, index=True, nullable=True)  # e.g. 120
    period_end = Column(Date, index=True, nullable=True)  # Financial Period End

    downloaded_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String, default="PENDING")  # PENDING, OK, NG
    error_message = Column(String, nullable=True)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Ensure one file type per doc_id has only one record (idempotency support)
    __table_args__ = (
        UniqueConstraint("doc_id", "file_type", name="uq_edinet_file_doc_type"),
    )

    def __repr__(self):
        return f"<EdinetFile(doc_id={self.doc_id}, type={self.file_type}, path={self.storage_path})>"
