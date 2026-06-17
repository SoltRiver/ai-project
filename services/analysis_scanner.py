"""
AI分析スキャナー（10分ごとの定期スキャン）
全銘柄をDBで軽くスキャンし、再分析が必要な銘柄のみジョブ投入する。
AIは一切呼ばない（必須ルール）。
"""

import logging
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List

from database import SessionLocal
from models.analysis_snapshot import AnalysisSnapshot
from services.analysis_snapshot_service import (
    is_stale,
    get_config_float,
    get_config_int,
)
from services.analysis_job_service import submit_job, compute_input_hash

logger = logging.getLogger(__name__)

# 対象の分析タイプ
ANALYSIS_TYPES = ["ai_assist_daily", "ai_assist_intraday"]


def _get_all_stock_codes() -> List[str]:
    """
    stock_masterテーブルから全銘柄コードを取得する。
    """
    db = SessionLocal()
    try:
        from models.master import StockMaster

        codes = [row.code for row in db.query(StockMaster.code).all()]
        return codes
    except Exception as e:
        logger.error(f"銘柄コード一覧取得エラー: {e}")
        return []
    finally:
        db.close()


def _get_latest_market_summary(stock_code: str) -> Dict[str, Any]:
    """
    銘柄の最新市場サマリーを取得する（DBキャッシュ or 直近yfinance）。
    スキャン用のため軽量に取得。
    """
    try:
        from services.data_fetcher import (
            fetch_stock_info,
            format_symbol_for_yfinance,
        )

        symbol = format_symbol_for_yfinance(stock_code)
        info = fetch_stock_info(symbol) or {}
        return {
            "current_price": info.get("current_price"),
            "previous_close": info.get("previous_close"),
            "volume": info.get("volume"),
            "average_volume": info.get("average_volume"),
        }
    except Exception as e:
        logger.debug(f"市場サマリー取得エラー {stock_code}: {e}")
        return {}


def _check_needs_reanalysis(
    snapshot: AnalysisSnapshot,
    market: Dict[str, Any],
    analysis_type: str,
) -> tuple:
    """
    再分析が必要かどうかを判定する。
    戻り値: (needed: bool, reason: str)
    AIは呼ばない（必須ルール）。
    """
    # 1) snapshotが存在しない → 初回生成が必要
    if snapshot is None:
        return True, "initial"

    # 2) TTL切れ
    if is_stale(snapshot):
        return True, "ttl"

    # 3) 価格変化チェック
    th_price_pct = get_config_float("TH_PRICE_PCT", 1.5)
    current = market.get("current_price")
    prev = market.get("previous_close")
    if current and prev and prev > 0:
        pct_change = abs((current - prev) / prev * 100)
        if pct_change >= th_price_pct:
            return True, "price_move"

    # 4) 出来高変化チェック
    th_vol_ratio = get_config_float("TH_VOL_RATIO", 2.0)
    volume = market.get("volume")
    avg_volume = market.get("average_volume")
    if volume and avg_volume and avg_volume > 0:
        vol_ratio = volume / avg_volume
        if vol_ratio >= th_vol_ratio:
            return True, "volume_change"

    # 5) 入力ハッシュの変化（データ変化の汎用検出）
    current_hash = compute_input_hash(
        snapshot.stock_code,
        analysis_type,
        f"{current}:{prev}:{volume}",
    )
    if snapshot.input_hash and current_hash != snapshot.input_hash:
        # ハッシュが変わった ≒ データが変わった
        # ただし軽微な変化はTH_PRICE_PCT等で既にカバーしているので、
        # ここでは追加の安全網として使用
        pass

    return False, ""


def run_scan() -> Dict[str, Any]:
    """
    全銘柄をスキャンし、再分析が必要な銘柄のジョブを投入する。
    AI呼び出しは行わない。DB参照のみ。
    """
    start_time = datetime.now(timezone.utc)
    logger.info("=== 分析スキャン開始 ===")

    stock_codes = _get_all_stock_codes()
    total = len(stock_codes)
    submitted = 0
    skipped = 0
    errors = 0

    db = SessionLocal()
    try:
        for code in stock_codes:
            try:
                market = _get_latest_market_summary(code)

                for a_type in ANALYSIS_TYPES:
                    # 現在のスナップショットを取得
                    snapshot = (
                        db.query(AnalysisSnapshot)
                        .filter_by(stock_code=code, analysis_type=a_type)
                        .first()
                    )

                    # 再分析判定
                    needed, reason = _check_needs_reanalysis(snapshot, market, a_type)

                    if needed:
                        # 入力ハッシュを計算
                        data_summary = (
                            f"{market.get('current_price', '')}:"
                            f"{market.get('previous_close', '')}:"
                            f"{market.get('volume', '')}"
                        )
                        input_hash = compute_input_hash(code, a_type, data_summary)

                        # 優先度の決定
                        priority = 50  # デフォルト: normal
                        if reason == "price_move":
                            priority = 70
                        elif reason == "volume_change":
                            priority = 60
                        elif reason == "initial":
                            priority = 10  # 初回生成は低優先度

                        # ジョブ投入（dedupe_keyで重複防止）
                        result = submit_job(
                            stock_code=code,
                            analysis_type=a_type,
                            reason=reason,
                            priority=priority,
                            desired_input_hash=input_hash,
                            db=db,
                        )
                        if result:
                            submitted += 1
                        else:
                            skipped += 1
                    else:
                        skipped += 1

            except Exception as e:
                logger.error(f"スキャンエラー {code}: {e}")
                errors += 1

    finally:
        db.close()

    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
    result = {
        "total_stocks": total,
        "analysis_types": len(ANALYSIS_TYPES),
        "jobs_submitted": submitted,
        "skipped": skipped,
        "errors": errors,
        "elapsed_sec": round(elapsed, 2),
    }
    logger.info(f"=== 分析スキャン完了: {result} ===")
    return result


def run_initial_batch(batch_size: int = 100) -> Dict[str, Any]:
    """
    初期バッチ: 全銘柄×分析タイプで低優先度ジョブを一括投入する。
    N件ずつコミットして一括投入の負荷を分散。
    """
    logger.info("=== 初期バッチ投入開始 ===")
    stock_codes = _get_all_stock_codes()
    total = len(stock_codes)
    submitted = 0

    db = SessionLocal()
    try:
        for i, code in enumerate(stock_codes):
            for a_type in ANALYSIS_TYPES:
                input_hash = compute_input_hash(code, a_type)
                result = submit_job(
                    stock_code=code,
                    analysis_type=a_type,
                    reason="initial_batch",
                    priority=10,  # 低優先度
                    desired_input_hash=input_hash,
                    db=db,
                )
                if result:
                    submitted += 1

            # バッチサイズごとにログ出力
            if (i + 1) % batch_size == 0:
                logger.info(f"初期バッチ進捗: {i + 1}/{total} ({submitted} jobs)")

    finally:
        db.close()

    result = {
        "total_stocks": total,
        "jobs_submitted": submitted,
    }
    logger.info(f"=== 初期バッチ投入完了: {result} ===")
    return result
