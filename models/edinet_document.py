from sqlalchemy import Column, Integer, String, Date, DateTime, Boolean, Text
from sqlalchemy.sql import func
from database import Base


class EdinetDocument(Base):
    __tablename__ = "edinet_documents"

    # API Key fields
    doc_id = Column(String(8), primary_key=True, index=True)  # docID is 8 chars usually
    target_date = Column(
        Date, index=True, nullable=False
    )  # The date searched (documents.json?date=...)

    # Metadata
    edinet_code = Column(String(8), index=True, nullable=True)  # E-Code
    sec_code = Column(String(5), index=True, nullable=True)  # 4 digits + 0
    jcn = Column(String(13), nullable=True)  # Corporate Number
    filer_name = Column(String(255), nullable=True)

    doc_type_code = Column(String(3), index=True, nullable=True)  # 120, 140 etc
    form_code = Column(String(6), nullable=True)
    doc_description = Column(Text, nullable=True)

    period_start = Column(Date, nullable=True)
    period_end = Column(Date, index=True, nullable=True)

    submit_datetime = Column(DateTime, nullable=True)

    # Status flags from API
    withdrawal_status = Column(String(1), nullable=True)  # "1" or "0"
    doc_info_edit_status = Column(String(1), nullable=True)
    disclosure_status = Column(String(1), nullable=True)

    # Content Availability Flags
    xbrl_flag = Column(
        String(1), nullable=True
    )  # "1" or "0" (Using String to match API/Postgres char(1))
    pdf_flag = Column(String(1), nullable=True)
    attach_doc_flag = Column(String(1), nullable=True)
    english_doc_flag = Column(String(1), nullable=True)
    csv_flag = Column(String(1), nullable=True)

    # System timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self):
        return f"<EdinetDocument(doc_id={self.doc_id}, filer={self.filer_name}, date={self.target_date})>"
