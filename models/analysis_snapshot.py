"""
AI分析スナップショットモデル
表示用の最新分析結果を保持する。SWRパターンにより即時表示に使用。
"""

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Index,
    UniqueConstraint,
)
from sqlalchemy.sql import func
from database import Base


class AnalysisSnapshot(Base):
    """
    分析スナップショット: 各銘柄×分析タイプごとの最新表示用データ。
    ユーザー閲覧時は常にこのテーブルから即時返却する。
    """
    __tablename__ = "analysis_snapshot"

    # 主キー（SQLite互換のためIntegerを使用）
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 銘柄コード（例: "7203"）
    stock_code = Column(String(20), nullable=False, index=True)

    # 分析タイプ（例: "ai_assist_daily", "ai_assist_intraday"）
    analysis_type = Column(String(50), nullable=False)

    # 入力データの基準時刻（例: ローソク足の最新時刻）
    asof_ts = Column(DateTime(timezone=True), nullable=False)

    # 生成完了時刻
    generated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # 有効期限（秒）。analysis_typeごとに異なる値を設定
    ttl_sec = Column(Integer, nullable=False, default=3600)

    # ステータス: ok / stale / running / error
    status = Column(String(20), nullable=False, default="ok")

    # 表示用コンテンツ（Markdown or プレーンテキスト）
    content_md = Column(Text, nullable=False, default="")

    # 入力データのSHA256ハッシュ（差分判定に使用）
    input_hash = Column(String(64), nullable=False, default="")

    # AI モデルバージョン（例: "gemini-1.5-flash"）
    model_version = Column(String(50), nullable=False, default="")

    # プロンプトバージョン（例: "v1.0"）
    prompt_version = Column(String(50), nullable=False, default="")

    # 最終エラー情報（前回成功結果を維持しつつエラーを記録）
    last_error_code = Column(String(50), nullable=True)
    last_error_message = Column(Text, nullable=True)

    # テーブル制約・インデックス
    __table_args__ = (
        # 銘柄×分析タイプで一意（常に最新1件のみ保持）
        UniqueConstraint("stock_code", "analysis_type", name="uq_snapshot_stock_type"),
        # 分析タイプ×生成日時で検索用
        Index("ix_snapshot_type_generated", "analysis_type", "generated_at"),
        # ステータス別検索用
        Index("ix_snapshot_status", "status"),
    )
