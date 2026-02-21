"""
イベントモデル

決算・配当などの銘柄関連イベントを管理するテーブル定義。
v1 では日付精度（DATE）のみ対応。
"""

from sqlalchemy import Column, Integer, String, Date, DateTime, UniqueConstraint, Index
from sqlalchemy.sql import func
from database import Base


class Event(Base):
    """
    銘柄イベントテーブル

    event_key = "{event_type}:{subtype}:{event_date}" で一意性を保証。
    """
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 銘柄コード（4桁）
    stock_code = Column(String(10), nullable=False, index=True)

    # 重複防止キー: "{event_type}:{subtype}:{event_date}"
    event_key = Column(String(100), nullable=False, index=True)

    # イベント種別: "EARNINGS" | "DIVIDEND"
    event_type = Column(String(20), nullable=False, index=True)

    # サブタイプ:
    #   EARNINGS: "ANNOUNCE"
    #   DIVIDEND: "LAST_CUM" | "EX_DATE" | "RECORD_DATE" | "PAY_DATE"
    subtype = Column(String(30), nullable=False, index=True)

    # イベント日（DATE精度のみ）
    event_date = Column(Date, nullable=False, index=True)

    # 短い表示名（例: "2026年3月期 決算発表"）
    title = Column(String(200), nullable=False)

    # 状態: "SCHEDULED" | "DONE" | "UNKNOWN"
    status = Column(String(20), nullable=False, default="SCHEDULED")

    # データソース: "jquants" | "calculated" | "manual" | "tdnet"
    source = Column(String(50), nullable=False)

    # ソース参照（URLや文書ID）
    source_ref = Column(String(500), nullable=True)

    # 備考（情報不足の補足など）
    notes = Column(String(500), nullable=True)

    # 最終検証日時（同期実行時に更新）
    last_verified_at = Column(DateTime(timezone=True), nullable=True)

    # タイムスタンプ
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # 一意制約: 同一銘柄・同一イベントキーの重複を防止
    __table_args__ = (
        UniqueConstraint("stock_code", "event_key", name="uq_stock_event_key"),
    )

    def __repr__(self):
        return f"<Event {self.stock_code} {self.event_key} ({self.status})>"
