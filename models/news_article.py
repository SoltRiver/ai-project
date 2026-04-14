"""
ニュース記事モデル
外部から取得したニュース記事の本体を保存するテーブル定義。
AI要約とは分離して管理し、再分析や重複排除に対応する。
"""

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, Index,
    UniqueConstraint,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base


class NewsArticle(Base):
    """
    ニュース記事テーブル
    yfinance等から取得した記事の本体を保持する。
    """
    __tablename__ = "news_articles"

    # 主キー
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 取得元ティッカー名（例: "^N225", "^DJI", "JPY=X"）
    source_name = Column(String(100), nullable=False, default="-")

    # 外部記事の一意ID（yfinanceのuuid等）
    source_article_id = Column(String(255), nullable=True)

    # 記事URL（重複排除の主キー）
    url = Column(String(1024), nullable=False, unique=True)

    # 記事タイトル
    title = Column(String(500), nullable=False, default="-")

    # 配信元（例: "Reuters", "Bloomberg"）
    publisher = Column(String(200), nullable=False, default="-")

    # 配信日時
    published_at = Column(DateTime(timezone=True), nullable=True)

    # 記事本文（サマリー含む）
    raw_text = Column(Text, nullable=False, default="")

    # 本文のSHA256ハッシュ（再分析判定に使用）
    raw_text_hash = Column(String(64), nullable=False, default="")

    # AI分析ステータス: fetched / queued / processing / summarized / failed / skipped
    ai_status = Column(String(20), nullable=False, default="fetched", index=True)

    # AI分析対象フラグ（ルールベースフィルタの結果）
    is_ai_target = Column(Boolean, nullable=False, default=False)

    # AI再試行回数
    retry_count = Column(Integer, nullable=False, default=0)

    # 最大再試行回数
    MAX_RETRY = 3

    # 直近エラーメッセージ
    last_error_message = Column(Text, nullable=True)

    # 最終分析日時
    last_analyzed_at = Column(DateTime(timezone=True), nullable=True)

    # 作成・更新日時
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True), nullable=False,
        server_default=func.now(), onupdate=func.now()
    )

    # リレーション
    ai_summaries = relationship("NewsAiSummary", back_populates="article", cascade="all, delete-orphan")
    related_tickers = relationship("NewsRelatedTicker", back_populates="article", cascade="all, delete-orphan")

    # テーブル制約・インデックス
    __table_args__ = (
        # ソース名＋外部記事IDでの重複検知用
        Index("ix_news_source_article", "source_name", "source_article_id"),
        # 配信日時での検索用
        Index("ix_news_published_at", "published_at"),
        # ステータス別検索用
        Index("ix_news_ai_status", "ai_status"),
    )

    def __repr__(self):
        return f"<NewsArticle(id={self.id}, title='{self.title[:30]}...', status='{self.ai_status}')>"
