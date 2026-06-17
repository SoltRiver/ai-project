from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    DateTime,
    func,
    Numeric,
    Index,
    JSON,
)
from database import Base


class EdinetMetricTimeseries(Base):
    __tablename__ = "edinet_metric_timeseries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sec_code = Column(String, nullable=False, index=True)
    metric_key = Column(String, nullable=False, index=True)
    period_end_year = Column(Integer, nullable=False)
    fiscal_year_label = Column(String, nullable=False)

    doc_id = Column(String(8), ForeignKey("edinet_documents.doc_id"), nullable=False)

    value_numeric = Column(Numeric, nullable=False)
    period_type = Column(String, nullable=False)
    duration_days = Column(Integer, nullable=True)

    selection_notes = Column(JSON, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index(
            "idx_timeseries_unique",
            "sec_code",
            "metric_key",
            "period_end_year",
            unique=True,
        ),
    )


class EdinetMetricComparison(Base):
    __tablename__ = "edinet_metric_comparison"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sec_code = Column(String, nullable=False, index=True)
    metric_key = Column(String, nullable=False)
    period_end_year = Column(Integer, nullable=False)

    doc_id = Column(String(8), ForeignKey("edinet_documents.doc_id"), nullable=False)

    yoy_abs = Column(Numeric, nullable=True)
    yoy_pct = Column(Numeric, nullable=True)
    turnaround_flag = Column(String, nullable=True)

    cagr_3y = Column(Numeric, nullable=True)
    cagr_5y = Column(Numeric, nullable=True)

    trend_label = Column(String, nullable=True)
    trend_reason = Column(String, nullable=True)

    source_docs = Column(JSON, nullable=False)
    calc_notes = Column(JSON, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index(
            "idx_comparison_unique",
            "sec_code",
            "metric_key",
            "period_end_year",
            unique=True,
        ),
    )
