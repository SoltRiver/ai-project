"""
AI分析スナップショットサービス
DBからスナップショットを即取得・更新するCRUD操作を提供する。
SWRパターンの「即時表示」部分を担当。
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import text

from database import SessionLocal
from models.analysis_snapshot import AnalysisSnapshot
from models.analysis_config import AnalysisConfig

logger = logging.getLogger(__name__)


def get_config_value(key: str, default: str = "", db: Session = None) -> str:
    """
    analysis_configテーブルから設定値を取得する。
    未登録の場合はdefaultを返す。
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    try:
        row = db.query(AnalysisConfig).filter_by(key=key).first()
        return row.value if row else default
    except Exception as e:
        logger.error(f"設定値取得エラー key={key}: {e}")
        return default
    finally:
        if close_db:
            db.close()


def get_config_int(key: str, default: int = 0, db: Session = None) -> int:
    """設定値をintで取得する。"""
    val = get_config_value(key, str(default), db)
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def get_config_float(key: str, default: float = 0.0, db: Session = None) -> float:
    """設定値をfloatで取得する。"""
    val = get_config_value(key, str(default), db)
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def get_snapshot(
    stock_code: str,
    analysis_type: str,
    db: Session = None,
) -> Optional[AnalysisSnapshot]:
    """
    指定した銘柄×分析タイプのスナップショットをDBから即取得する。
    存在しない場合はNoneを返す。
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    try:
        return (
            db.query(AnalysisSnapshot)
            .filter_by(stock_code=stock_code, analysis_type=analysis_type)
            .first()
        )
    except Exception as e:
        logger.error(f"スナップショット取得エラー {stock_code}/{analysis_type}: {e}")
        return None
    finally:
        if close_db:
            db.close()


def get_snapshots_for_stock(
    stock_code: str, db: Session = None
) -> list:
    """
    指定した銘柄の全分析タイプのスナップショットを取得する。
    銘柄詳細画面でまとめて表示する際に使用。
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    try:
        return (
            db.query(AnalysisSnapshot)
            .filter_by(stock_code=stock_code)
            .all()
        )
    except Exception as e:
        logger.error(f"スナップショット一覧取得エラー {stock_code}: {e}")
        return []
    finally:
        if close_db:
            db.close()


def is_stale(snapshot: Optional[AnalysisSnapshot]) -> bool:
    """
    スナップショットが古いかどうかを判定する。
    - snapshotがNone → True（未生成=stale扱い）
    - generated_at + ttl_sec < now → True
    - status が 'error' or 'stale' → True
    """
    if snapshot is None:
        return True

    if snapshot.status in ("error", "stale"):
        return True

    now = datetime.now(timezone.utc)
    generated = snapshot.generated_at
    # タイムゾーン情報がない場合はUTCとして扱う
    if generated.tzinfo is None:
        generated = generated.replace(tzinfo=timezone.utc)

    from datetime import timedelta
    expiry = generated + timedelta(seconds=snapshot.ttl_sec)
    return now > expiry


def upsert_snapshot(
    stock_code: str,
    analysis_type: str,
    content_md: str,
    asof_ts: datetime,
    input_hash: str,
    model_version: str = "",
    prompt_version: str = "",
    ttl_sec: int = 3600,
    status: str = "ok",
    db: Session = None,
) -> Optional[AnalysisSnapshot]:
    """
    スナップショットをupsert（存在すれば更新、なければ挿入）する。
    ワーカーがAI生成完了後に呼び出す。
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    try:
        existing = (
            db.query(AnalysisSnapshot)
            .filter_by(stock_code=stock_code, analysis_type=analysis_type)
            .first()
        )
        now = datetime.now(timezone.utc)

        if existing:
            # 既存レコードを更新
            existing.content_md = content_md
            existing.asof_ts = asof_ts
            existing.generated_at = now
            existing.input_hash = input_hash
            existing.model_version = model_version
            existing.prompt_version = prompt_version
            existing.ttl_sec = ttl_sec
            existing.status = status
            # 成功時はエラー情報をクリア
            if status == "ok":
                existing.last_error_code = None
                existing.last_error_message = None
            db.commit()
            db.refresh(existing)
            return existing
        else:
            # 新規レコードを挿入
            new_snapshot = AnalysisSnapshot(
                stock_code=stock_code,
                analysis_type=analysis_type,
                content_md=content_md,
                asof_ts=asof_ts,
                generated_at=now,
                input_hash=input_hash,
                model_version=model_version,
                prompt_version=prompt_version,
                ttl_sec=ttl_sec,
                status=status,
            )
            db.add(new_snapshot)
            db.commit()
            db.refresh(new_snapshot)
            return new_snapshot
    except Exception as e:
        logger.error(f"スナップショットupsertエラー {stock_code}/{analysis_type}: {e}")
        db.rollback()
        return None
    finally:
        if close_db:
            db.close()


def update_snapshot_error(
    stock_code: str,
    analysis_type: str,
    error_code: str,
    error_message: str,
    db: Session = None,
) -> None:
    """
    スナップショットのエラー情報のみ更新する。
    前回のcontent_mdは維持し、last_error_*のみ記録する。
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    try:
        existing = (
            db.query(AnalysisSnapshot)
            .filter_by(stock_code=stock_code, analysis_type=analysis_type)
            .first()
        )
        if existing:
            existing.last_error_code = error_code
            existing.last_error_message = error_message
            db.commit()
    except Exception as e:
        logger.error(f"スナップショットエラー更新失敗 {stock_code}/{analysis_type}: {e}")
        db.rollback()
    finally:
        if close_db:
            db.close()


def snapshot_to_dict(snapshot: Optional[AnalysisSnapshot]) -> Dict[str, Any]:
    """
    スナップショットをテンプレート用dict形式に変換する。
    Noneの場合はプレースホルダー用の辞書を返す。
    """
    if snapshot is None:
        return {
            "exists": False,
            "stock_code": "-",
            "analysis_type": "-",
            "content_md": "",
            "generated_at": "-",
            "asof_ts": "-",
            "status": "none",
            "is_stale": True,
            "last_error_code": None,
            "last_error_message": None,
        }

    stale = is_stale(snapshot)
    generated_str = (
        snapshot.generated_at.strftime("%Y/%m/%d %H:%M")
        if snapshot.generated_at else "-"
    )
    asof_str = (
        snapshot.asof_ts.strftime("%Y/%m/%d %H:%M")
        if snapshot.asof_ts else "-"
    )

    return {
        "exists": True,
        "stock_code": snapshot.stock_code,
        "analysis_type": snapshot.analysis_type,
        "content_md": snapshot.content_md,
        "generated_at": generated_str,
        "asof_ts": asof_str,
        "status": "stale" if stale else snapshot.status,
        "is_stale": stale,
        "model_version": snapshot.model_version or "-",
        "prompt_version": snapshot.prompt_version or "-",
        "last_error_code": snapshot.last_error_code,
        "last_error_message": snapshot.last_error_message,
    }
