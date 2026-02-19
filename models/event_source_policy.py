"""
イベントソースポリシー＋冪等管理モデル

合法性チェック（auto_fetch_allowed + expires_at）と
日付単位の巡回状態管理を行うSQLAlchemyモデル。
"""

from sqlalchemy import Column, String, Text, Boolean, DateTime, Date, Integer
from sqlalchemy.sql import func
from database import Base


class EventSourcePolicy(Base):
    """
    ソース管理テーブル（合法性強制チェック）
    自動取得の可否・有効期限・法的根拠を管理する。
    """
    __tablename__ = "event_source_policy"

    # ソース名（主キー）: 例 "EDINET_API", "RSS_JPX", "MANUAL", "TDNET_API"
    source_name = Column(String(100), primary_key=True)
    # ソース種別: EDINET_API / RSS / MANUAL / TDNET_API
    source_type = Column(String(50), nullable=False)
    # 法的根拠: Official API / Official RSS / Manual / Paid API
    legal_basis = Column(String(255), nullable=False)
    # 利用規約URL
    terms_url = Column(Text, nullable=True)
    # robots.txt URL
    robots_url = Column(Text, nullable=True)
    # 自動取得許可フラグ
    auto_fetch_allowed = Column(Boolean, nullable=False, default=False)
    # 確認日時
    checked_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # 承認者
    approved_by = Column(String(100), nullable=False, default="SYSTEM")
    # 有効期限（checked_at + 180日を推奨）
    expires_at = Column(DateTime(timezone=True), nullable=False)


class EventIngestState(Base):
    """
    冪等管理テーブル（日付単位の取得状態）
    同一ソース・同一日付の重複巡回を防止する。
    """
    __tablename__ = "event_ingest_state"

    # ソース名（event_source_policyと紐づく）
    source_name = Column(String(100), primary_key=True)
    # 巡回日付
    ingest_date = Column(Date, primary_key=True)
    # 処理状態: PENDING / PROCESSING / DONE / ERROR
    status = Column(String(20), nullable=False, default="PENDING")
    # 取得件数（EDINETから取得したドキュメント数）
    fetched_count = Column(Integer, default=0)
    # 抽出件数（イベントとして抽出した件数）
    extracted_count = Column(Integer, default=0)
    # エラーメッセージ
    error_message = Column(Text, nullable=True)
    # 処理開始日時
    started_at = Column(DateTime(timezone=True), nullable=True)
    # 処理完了日時
    completed_at = Column(DateTime(timezone=True), nullable=True)
    # 作成日時
    created_at = Column(DateTime(timezone=True), server_default=func.now())
