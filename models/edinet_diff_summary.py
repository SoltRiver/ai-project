from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy import ForeignKey
from database import Base


class EdinetDiffSummary(Base):
    """
    EDINET書類間の差分比較結果を保持するテーブル。
    生成済みの差分データをキャッシュし、再利用する。
    json_payload に固定6項目と変化大3件の詳細を格納する。
    """

    __tablename__ = "edinet_diff_summary"

    id = Column(Integer, primary_key=True, index=True)

    # 比較対象の書類ID
    current_doc_id = Column(
        String(8),
        ForeignKey("edinet_documents.doc_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # 前回書類ID（初回取得の場合は NULL）
    prev_doc_id = Column(String(8), nullable=True)

    # 生成メタデータ
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    # ステータス: ok（全指標取得成功）/ partial（一部欠損あり）/ failed（生成自体が失敗）
    status = Column(String(10), nullable=False, default="ok")

    # 差分データ全体を JSON 形式で格納
    json_payload = Column(JSON, nullable=True)

    # 注意文やエラー情報
    notes = Column(Text, nullable=True)

    # 同一書類に対する差分は1レコードのみ
    __table_args__ = (
        UniqueConstraint("current_doc_id", name="uq_diff_summary_current_doc"),
    )

    def __repr__(self):
        return f"<DiffSummary(current={self.current_doc_id}, prev={self.prev_doc_id}, status={self.status})>"
