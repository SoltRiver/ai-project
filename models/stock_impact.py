
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, CHAR
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class StockNews(Base):
    __tablename__ = "stock_news"

    id = Column(Integer, primary_key=True, index=True)
    sec_code = Column(CHAR(5), index=True, nullable=False)
    source_name = Column(String(255), nullable=False)
    title = Column(Text, nullable=False)
    url = Column(Text, nullable=True)
    published_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    analysis = relationship("StockNewsAnalysis", uselist=False, back_populates="news", cascade="all, delete-orphan")

class StockNewsAnalysis(Base):
    __tablename__ = "stock_news_analysis"

    news_id = Column(Integer, ForeignKey("stock_news.id", ondelete="CASCADE"), primary_key=True)
    impact_type = Column(String(20), nullable=False) # POSITIVE, NEGATIVE, NEUTRAL
    impact_strength = Column(String(10), nullable=False) # HIGH, MEDIUM, LOW
    summary_2lines = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    news = relationship("StockNews", back_populates="analysis")


class StockEvent(Base):
    __tablename__ = "stock_event"

    id = Column(Integer, primary_key=True, index=True)
    sec_code = Column(CHAR(5), index=True, nullable=False)
    event_type = Column(String(50), nullable=False)
    title = Column(Text, nullable=False)
    announced_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    analysis = relationship("StockEventAnalysis", uselist=False, back_populates="event", cascade="all, delete-orphan")

class StockEventAnalysis(Base):
    __tablename__ = "stock_event_analysis"

    event_id = Column(Integer, ForeignKey("stock_event.id", ondelete="CASCADE"), primary_key=True)
    impact_type = Column(String(20), nullable=False) # POSITIVE, NEGATIVE, NEUTRAL
    impact_strength = Column(String(10), nullable=False) # HIGH, MEDIUM, LOW
    summary_2lines = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    event = relationship("StockEvent", back_populates="analysis")
