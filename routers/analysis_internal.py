"""
AI分析SWRシステム用ルーター
内部エンドポイント（スキャン起動・ワーカー起動・初期バッチ・統計）と
画面表示用パーシャルエンドポイントを提供する。
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db

import logging

logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory="templates")
router = APIRouter()


# ============================================================
# 画面表示用パーシャルエンドポイント（htmx swap用）
# ============================================================


@router.get("/partials/analysis/{code}", response_class=HTMLResponse)
async def get_analysis_partial(
    code: str,
    request: Request,
    type: str = "ai_assist_daily",
    db: Session = Depends(get_db),
):
    """
    分析ブロックだけ返す（htmx swap用）。
    常にDBスナップショットを即返す。古い場合はジョブ投入してバックグラウンド更新。
    """
    from services.analysis_snapshot_service import (
        get_snapshot,
        is_stale,
        snapshot_to_dict,
    )
    from services.analysis_job_service import submit_job, compute_input_hash

    # スナップショットを即取得
    snapshot = get_snapshot(code, type, db)
    snapshot_data = snapshot_to_dict(snapshot)

    # stale判定 → ジョブ投入
    if is_stale(snapshot):
        input_hash = compute_input_hash(code, type)
        submit_job(
            stock_code=code,
            analysis_type=type,
            reason="user_view",
            priority=100,  # 閲覧トリガーは最高優先度
            desired_input_hash=input_hash,
            db=db,
        )
        snapshot_data["status"] = "stale"

    return templates.TemplateResponse(
        "stocks/partials/_analysis_card.html",
        {
            "request": request,
            "stock": {"code": code},
            "analysis": snapshot_data,
            "analysis_type": type,
        },
    )


# ============================================================
# 内部API（認証は将来追加。現状は内部ネットワーク前提）
# ============================================================


@router.post("/internal/jobs/scan")
async def trigger_scan():
    """
    10分スキャンを手動起動する。
    全銘柄を走査し、再分析が必要な銘柄のジョブを投入。
    """
    try:
        from services.analysis_scanner import run_scan

        result = run_scan()
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"スキャン起動エラー: {e}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500,
        )


@router.post("/internal/jobs/worker")
async def trigger_worker(count: int = 1):
    """
    ワーカーを手動起動する。
    count件のジョブを処理する。
    """
    try:
        from services.analysis_worker import run_worker_cycle

        results = []
        for _ in range(count):
            result = run_worker_cycle()
            results.append(result)
            if result["status"] in ("no_job", "circuit_breaker_open"):
                break
        return JSONResponse(content={"results": results})
    except Exception as e:
        logger.error(f"ワーカー起動エラー: {e}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500,
        )


@router.post("/internal/jobs/init-batch")
async def trigger_init_batch():
    """
    初期バッチ投入を起動する。
    全銘柄×分析タイプで低優先度ジョブを一括投入。
    """
    try:
        from services.analysis_scanner import run_initial_batch

        result = run_initial_batch()
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"初期バッチ投入エラー: {e}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500,
        )


@router.get("/internal/jobs/stats")
async def get_stats():
    """
    ジョブキューの統計情報を返す。
    運用監視用。
    """
    try:
        from services.analysis_job_service import get_job_stats

        stats = get_job_stats()
        return JSONResponse(content=stats)
    except Exception as e:
        logger.error(f"統計取得エラー: {e}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500,
        )
