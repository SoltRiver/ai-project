"""
AI分析ジョブサービス
ジョブの投入（重複防止）、ワーカーによる取得・ロック・完了/失敗処理を提供する。
"""

import hashlib
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import and_

from database import SessionLocal
from models.analysis_job import AnalysisJob
from services.analysis_snapshot_service import get_config_int

logger = logging.getLogger(__name__)


def compute_dedupe_key(
    stock_code: str, analysis_type: str, desired_input_hash: str
) -> str:
    """
    重複排除キーを計算する。
    同一銘柄×分析タイプ×入力ハッシュで同一キーになる。
    """
    raw = f"{stock_code}:{analysis_type}:{desired_input_hash}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def compute_input_hash(
    stock_code: str, analysis_type: str, data_summary: str = ""
) -> str:
    """
    入力データのハッシュを計算する。
    data_summaryは価格・指標等の要約文字列。
    """
    raw = f"{stock_code}:{analysis_type}:{data_summary}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def submit_job(
    stock_code: str,
    analysis_type: str,
    reason: str = "ttl",
    priority: int = 50,
    desired_asof_ts: Optional[datetime] = None,
    desired_input_hash: str = "",
    db: Session = None,
) -> bool:
    """
    分析ジョブを投入する。
    dedupe_keyで重複をDB制約で防止（ON CONFLICT DO NOTHINGと同等）。
    戻り値: True=投入成功, False=重複で投入不要 or エラー

    重要: 同一銘柄×分析タイプで同じ入力ハッシュのジョブが既に
    queued/running なら投入しない。
    """
    if desired_asof_ts is None:
        desired_asof_ts = datetime.now(timezone.utc)

    if not desired_input_hash:
        desired_input_hash = compute_input_hash(stock_code, analysis_type)

    dedupe_key = compute_dedupe_key(stock_code, analysis_type, desired_input_hash)

    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        # 既存のqueued/runningジョブをチェック（dedupe_keyベース）
        existing = (
            db.query(AnalysisJob)
            .filter(
                AnalysisJob.dedupe_key == dedupe_key,
                AnalysisJob.status.in_(["queued", "running"]),
            )
            .first()
        )

        if existing:
            # 既に同一ジョブがキュー or 実行中 → 投入不要
            # ただし優先度が高い場合は優先度を上書き
            if priority > existing.priority:
                existing.priority = priority
                existing.reason = reason
                db.commit()
                logger.info(
                    f"ジョブ優先度更新: {stock_code}/{analysis_type} "
                    f"priority={priority} reason={reason}"
                )
            return False

        # 新規ジョブ投入
        new_job = AnalysisJob(
            stock_code=stock_code,
            analysis_type=analysis_type,
            priority=priority,
            reason=reason,
            desired_asof_ts=desired_asof_ts,
            desired_input_hash=desired_input_hash,
            dedupe_key=dedupe_key,
            status="queued",
            attempts=0,
            queued_at=datetime.now(timezone.utc),
        )
        db.add(new_job)
        db.commit()
        logger.info(
            f"ジョブ投入: {stock_code}/{analysis_type} "
            f"priority={priority} reason={reason}"
        )
        return True

    except Exception as e:
        # UniqueConstraint違反（並行投入時のrace condition）はエラーではない
        if "UNIQUE" in str(e).upper() or "unique" in str(e).lower():
            logger.debug(f"ジョブ重複スキップ: {stock_code}/{analysis_type}")
            db.rollback()
            return False
        logger.error(f"ジョブ投入エラー: {stock_code}/{analysis_type}: {e}")
        db.rollback()
        return False
    finally:
        if close_db:
            db.close()


def fetch_next_job(worker_id: str, db: Session = None) -> Optional[AnalysisJob]:
    """
    次に処理すべきジョブを1件取得し、ロックする。
    locked_until方式の協調ロック（SQLite/PostgreSQL両対応）。
    """
    lock_sec = get_config_int("WORKER_LOCK_SEC", 120, db)
    now = datetime.now(timezone.utc)

    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        # ロック期限切れのジョブをqueuedに戻す
        expired_jobs = (
            db.query(AnalysisJob)
            .filter(
                AnalysisJob.status == "running",
                AnalysisJob.locked_until < now,
            )
            .all()
        )
        for j in expired_jobs:
            j.status = "queued"
            j.locked_by = None
            j.locked_until = None
            logger.warning(f"ロック期限切れジョブをリセット: job_id={j.job_id}")
        if expired_jobs:
            db.commit()

        # 優先度順でqueuedジョブを1件取得
        job = (
            db.query(AnalysisJob)
            .filter(AnalysisJob.status == "queued")
            .order_by(AnalysisJob.priority.desc(), AnalysisJob.queued_at.asc())
            .first()
        )

        if job is None:
            return None

        # ロック取得
        job.status = "running"
        job.locked_by = worker_id
        job.locked_until = now + timedelta(seconds=lock_sec)
        job.started_at = now
        job.attempts += 1
        db.commit()
        db.refresh(job)
        return job

    except Exception as e:
        logger.error(f"ジョブ取得エラー: {e}")
        db.rollback()
        return None
    finally:
        if close_db:
            db.close()


def complete_job(job_id: int, db: Session = None) -> None:
    """ジョブを完了状態にする。"""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    try:
        job = db.query(AnalysisJob).filter_by(job_id=job_id).first()
        if job:
            job.status = "done"
            job.finished_at = datetime.now(timezone.utc)
            job.locked_by = None
            job.locked_until = None
            db.commit()
    except Exception as e:
        logger.error(f"ジョブ完了エラー job_id={job_id}: {e}")
        db.rollback()
    finally:
        if close_db:
            db.close()


def fail_job(
    job_id: int,
    error_code: str = "",
    error_message: str = "",
    db: Session = None,
) -> None:
    """
    ジョブを失敗状態にする。
    MAX_ATTEMPTSを超えた場合はcanceledにする。
    """
    max_attempts = get_config_int("MAX_ATTEMPTS", 3, db)

    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    try:
        job = db.query(AnalysisJob).filter_by(job_id=job_id).first()
        if job:
            job.last_error_code = error_code
            job.last_error_message = error_message
            job.locked_by = None
            job.locked_until = None
            job.finished_at = datetime.now(timezone.utc)

            if job.attempts >= max_attempts:
                # リトライ上限超過 → canceled
                job.status = "canceled"
                logger.warning(
                    f"ジョブcanceled（リトライ上限超過）: job_id={job_id} "
                    f"attempts={job.attempts}"
                )
            else:
                # 再試行可能 → queuedに戻す
                job.status = "queued"
                job.finished_at = None
                logger.info(
                    f"ジョブ失敗→再キュー: job_id={job_id} "
                    f"attempts={job.attempts}/{max_attempts}"
                )
            db.commit()
    except Exception as e:
        logger.error(f"ジョブ失敗処理エラー job_id={job_id}: {e}")
        db.rollback()
    finally:
        if close_db:
            db.close()


def get_job_stats(db: Session = None) -> dict:
    """
    ジョブキューの統計情報を取得する。
    監視・運用ダッシュボード用。
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    try:
        from sqlalchemy import func

        stats = {}
        for status_val in ["queued", "running", "done", "failed", "canceled"]:
            count = (
                db.query(func.count(AnalysisJob.job_id))
                .filter(AnalysisJob.status == status_val)
                .scalar()
            )
            stats[status_val] = count or 0
        stats["total"] = sum(stats.values())
        return stats
    except Exception as e:
        logger.error(f"ジョブ統計取得エラー: {e}")
        return {"error": str(e)}
    finally:
        if close_db:
            db.close()
