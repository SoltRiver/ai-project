"""
AI分析設定テーブルモデル
閾値・TTL・リトライ上限などの運用パラメータを管理する。
環境変数よりも柔軟に、DBから運用調整できるようにする。
"""

from sqlalchemy import Column, String, Text
from database import Base


class AnalysisConfig(Base):
    """
    分析設定: key-value形式の運用パラメータ。
    閾値やTTLなどを運用中にDB上で変更可能にする。
    """

    __tablename__ = "analysis_config"

    # 設定キー（例: "TH_PRICE_PCT", "TTL_DAILY_SEC"）
    key = Column(String(100), primary_key=True)

    # 設定値（文字列で格納。利用側で適切な型に変換する）
    value = Column(Text, nullable=False)


# 初期投入するデフォルト設定値
DEFAULT_CONFIG = {
    # 価格変化の閾値（%）: この割合以上変動で再分析対象
    "TH_PRICE_PCT": "1.5",
    # 出来高倍率の閾値: 直近平均比この倍率以上で再分析対象
    "TH_VOL_RATIO": "2.0",
    # イントラデイ分析のTTL（秒）: 1時間
    "TTL_INTRADAY_SEC": "3600",
    # 日次分析のTTL（秒）: 24時間
    "TTL_DAILY_SEC": "86400",
    # ワーカーのロック有効期間（秒）: 2分
    "WORKER_LOCK_SEC": "120",
    # 最大リトライ回数: これを超えるとcanceled
    "MAX_ATTEMPTS": "3",
    # サーキットブレーカ: 連続失敗でAI呼び出し停止する閾値
    "CIRCUIT_BREAKER_THRESHOLD": "10",
    # サーキットブレーカのクールダウン（秒）
    "CIRCUIT_BREAKER_COOLDOWN_SEC": "300",
}
