"""
ニュースAI要約モデル
AI要約結果を記事本体と分離して保存するテーブル定義。
モデル変更やプロンプト変更に伴う再生成に対応する。
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base


class NewsAiSummary(Base):
    """
    ニュースAI要約テーブル
    1つの記事に対して、モデル×プロンプトバージョンの組み合わせで
    複数の要約を保持可能。最新のものを画面に表示する。
    """

    __tablename__ = "news_ai_summaries"

    # 主キー
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 対象記事への外部キー
    news_article_id = Column(
        Integer,
        ForeignKey("news_articles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 使用したAIモデル名（例: "gemini-1.5-flash", "gpt-4o-mini"）
    model_name = Column(String(100), nullable=False, default="-")

    # プロンプトバージョン（再生成判定に使用）
    prompt_version = Column(String(20), nullable=False, default="v1.0")

    # AI入力テキストのSHA256ハッシュ（前処理後の入力が同じなら再要約しない）
    input_hash = Column(String(64), nullable=False, default="")

    # 要約テキスト（80文字以内を目標）
    summary = Column(Text, nullable=False, default="")

    # 日本語翻訳タイトル
    translated_title = Column(String(500), nullable=True)

    # センチメント: positive / negative / neutral
    sentiment = Column(String(20), nullable=False, default="neutral")

    # センチメントの理由
    reason = Column(Text, nullable=False, default="")

    # 分析ステータス: success / failed
    analysis_status = Column(String(20), nullable=False, default="success")

    # 分析完了日時
    analyzed_at = Column(DateTime(timezone=True), nullable=True)

    # 作成・更新日時
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # リレーション
    article = relationship("NewsArticle", back_populates="ai_summaries")

    # テーブル制約・インデックス
    __table_args__ = (
        # 記事×モデル×プロンプトバージョンで検索用
        Index(
            "ix_summary_article_model",
            "news_article_id",
            "model_name",
            "prompt_version",
        ),
    )

    def __repr__(self):
        return f"<NewsAiSummary(id={self.id}, article_id={self.news_article_id}, status='{self.analysis_status}')>"
