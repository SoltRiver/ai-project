"""
ニュース関連銘柄モデル
ルールベースまたはAIで抽出された影響銘柄の情報を保存するテーブル定義。
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Text,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base


class NewsRelatedTicker(Base):
    """
    ニュース関連銘柄テーブル
    1つの記事に対して複数の影響銘柄を紐付ける。
    抽出方法（ルールベース/AI/ハイブリッド）を記録する。
    """

    __tablename__ = "news_related_tickers"

    # 主キー
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 対象記事への外部キー
    news_article_id = Column(
        Integer,
        ForeignKey("news_articles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 証券コード（例: "7203"）
    ticker_code = Column(String(20), nullable=False, default="-")

    # 企業名（例: "トヨタ自動車"）
    company_name = Column(String(200), nullable=False, default="-")

    # 影響タイプ: positive / negative
    impact_type = Column(String(20), nullable=False, default="positive")

    # 信頼度（0.0〜1.0）
    confidence = Column(Float, nullable=False, default=0.5)

    # 抽出手法: rule / ai / hybrid
    extraction_type = Column(String(20), nullable=False, default="rule")

    # 抽出理由
    reason = Column(Text, nullable=False, default="")

    # 作成日時
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # リレーション
    article = relationship("NewsArticle", back_populates="related_tickers")

    # テーブル制約・インデックス
    __table_args__ = (
        # 銘柄コードでの検索用
        Index("ix_related_ticker_code", "ticker_code"),
        # 記事×銘柄の組み合わせ検索用
        Index("ix_related_article_ticker", "news_article_id", "ticker_code"),
    )

    def __repr__(self):
        return f"<NewsRelatedTicker(id={self.id}, ticker='{self.ticker_code}', company='{self.company_name}')>"
