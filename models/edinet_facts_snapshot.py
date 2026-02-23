
from sqlalchemy import Column, Integer, String, DateTime, Numeric, Text, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy import ForeignKey
from database import Base


class EdinetFactsSnapshot(Base):
    """
    EDINET書類から抽出した財務指標の正規化スナップショット。
    EdinetFinancialHighlightから変換し、単位正規化済みの値を保持する。
    差分比較の基盤データとして使用する。
    """
    __tablename__ = "edinet_facts_snapshot"

    id = Column(Integer, primary_key=True, index=True)

    # 書類と銘柄の紐付け
    doc_id = Column(
        String(8),
        ForeignKey("edinet_documents.doc_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    stock_code = Column(String(5), index=True, nullable=True)  # sec_code を正規化（4桁 or 5桁）

    # 指標情報
    metric_key = Column(String(50), nullable=False, index=True)  # revenue, operating_profit 等
    value = Column(Numeric, nullable=True)  # 単位正規化済みの数値（JPY基準）
    unit = Column(String(20), nullable=True)  # 正規化後の単位（通常は "JPY"）

    # 連結区分（consolidated / non_consolidated / unknown）
    consolidation_scope = Column(String(30), nullable=True, default="unknown")

    # 取得元の追跡情報
    source_locator = Column(Text, nullable=True)  # 元の XBRL concept 参照

    # システムタイムスタンプ
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # ユニーク制約：同一書類の同一指標は1レコードのみ
    __table_args__ = (
        UniqueConstraint('doc_id', 'metric_key', name='uq_facts_snapshot_doc_metric'),
    )

    def __repr__(self):
        return f"<FactsSnapshot(doc={self.doc_id}, key={self.metric_key}, val={self.value})>"
