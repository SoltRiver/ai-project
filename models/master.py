from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from database import Base


class StockMaster(Base):
    __tablename__ = "stock_master"

    code = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    market = Column(String, nullable=True)  # e.g. "Prime", "Standard"
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AppSyncStatus(Base):
    """
    Tracks the status of data synchronization tasks.
    Intended to be a single-row table for global status.
    """

    __tablename__ = "app_sync_status"

    id = Column(Integer, primary_key=True, default=1)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    last_sync_status = Column(String, nullable=True)  # SUCCESS, FAILED, SKIPPED
    last_sync_error = Column(String, nullable=True)
    source = Column(String, nullable=True)  # "seed", "jquants"
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
