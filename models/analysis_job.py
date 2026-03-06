"""
AI分析ジョブキューモデル
再分析が必要な銘柄のジョブを管理する。dedupe_keyで重複防止。
"""

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Index,
    UniqueConstraint,
)
from sqlalchemy.sql import func
from database import Base


class AnalysisJob(Base):
    """
    分析ジョブキュー: 再分析が必要な銘柄の処理要求を管理。
    ワーカーが優先度順に取り出してAI生成を実行する。
    """
    __tablename__ = "analysis_job"

    # 主キー（SQLite互換のためIntegerを使用）
    job_id = Column(Integer, primary_key=True, autoincrement=True)

    # 銘柄コード
    stock_code = Column(String(20), nullable=False, index=True)

    # 分析タイプ
    analysis_type = Column(String(50), nullable=False)

    # 優先度（0=low, 50=normal, 100=high）
    priority = Column(Integer, nullable=False, default=50)

    # 投入理由（ttl / price_move / signal_change / user_view / event / volume_change）
    reason = Column(String(50), nullable=False, default="ttl")

    # 希望する入力データ基準時刻
    desired_asof_ts = Column(DateTime(timezone=True), nullable=False)

    # 希望する入力データハッシュ（同じなら再生成不要）
    desired_input_hash = Column(String(64), nullable=False)

    # 重複排除キー: hash(stock_code + analysis_type + desired_input_hash)
    dedupe_key = Column(String(64), nullable=False)

    # ジョブステータス: queued / running / done / failed / canceled
    status = Column(String(20), nullable=False, default="queued")

    # 試行回数
    attempts = Column(Integer, nullable=False, default=0)

    # タイムスタンプ
    queued_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    # 協調ロック（locked_until方式。SQLite/PostgreSQL両対応）
    locked_by = Column(String(100), nullable=True)
    locked_until = Column(DateTime(timezone=True), nullable=True)

    # エラー情報
    last_error_code = Column(String(50), nullable=True)
    last_error_message = Column(Text, nullable=True)

    # テーブル制約・インデックス
    __table_args__ = (
        # 重複排除キーの一意制約（INSERT ON CONFLICT DO NOTHINGで使用）
        UniqueConstraint("dedupe_key", name="uq_job_dedupe_key"),
        # ワーカーがジョブを取得する際の検索用（ステータス→優先度高い順→投入時刻順）
        Index("ix_job_queue", "status", "priority", "queued_at"),
        # ロック期限切れの検出用
        Index("ix_job_locked_until", "locked_until"),
    )
