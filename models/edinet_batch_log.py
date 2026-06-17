"""
EDINET 日次バッチ実行ログモデル

1日100リクエストのAPIバジェット消費を追跡し、
各フェーズ（日次スキャン / シード銘柄処理 / バックフィル）の
進捗と結果を記録する。
"""

from sqlalchemy import Column, Integer, String, Date, DateTime, JSON
from sqlalchemy.sql import func
from database import Base


class EdinetBatchLog(Base):
    """日次バッチの実行ログ"""

    __tablename__ = "edinet_batch_logs"

    id = Column(Integer, primary_key=True, index=True)

    # バッチ実行日（この日のバジェットに計上される）
    batch_date = Column(Date, nullable=False, index=True)

    # フェーズ: A=日次スキャン, B=シード銘柄処理, C=バックフィル
    phase = Column(String, nullable=False)

    # 統計カウンタ
    api_calls = Column(Integer, default=0)  # 消費したAPIリクエスト数
    docs_found = Column(Integer, default=0)  # 発見した書類数
    docs_downloaded = Column(Integer, default=0)  # ダウンロード成功数
    docs_processed = Column(Integer, default=0)  # 処理完了数（XBRL解析等）
    errors = Column(Integer, default=0)  # エラー数

    # ステータス: RUNNING / DONE / FAILED / SKIPPED
    status = Column(String, default="RUNNING")

    # 詳細データ（処理した銘柄リスト、エラー詳細等）
    detail_json = Column(JSON, nullable=True)

    # タイムスタンプ
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return (
            f"<EdinetBatchLog(date={self.batch_date}, phase={self.phase}, "
            f"api={self.api_calls}, status={self.status})>"
        )
