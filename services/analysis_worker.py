"""
AI分析ワーカー
ジョブキューからジョブを1件取得し、AI生成を実行してスナップショットをupsertする。
analysis_typeに応じてdaily（重め）/ intraday（軽量）のプロンプトを使い分ける。
"""

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from database import SessionLocal
from services.analysis_job_service import fetch_next_job, complete_job, fail_job
from services.analysis_snapshot_service import (
    upsert_snapshot,
    update_snapshot_error,
    get_config_int,
    get_config_value,
)

logger = logging.getLogger(__name__)

# サーキットブレーカの状態（メモリ内。プロセス再起動でリセット）
_circuit_breaker_failures = 0
_circuit_breaker_last_open = None


def _check_circuit_breaker() -> bool:
    """
    サーキットブレーカが開いている場合はTrueを返す（AI呼び出し停止）。
    """
    global _circuit_breaker_failures, _circuit_breaker_last_open

    threshold = get_config_int("CIRCUIT_BREAKER_THRESHOLD", 10)
    cooldown_sec = get_config_int("CIRCUIT_BREAKER_COOLDOWN_SEC", 300)

    if _circuit_breaker_failures < threshold:
        return False

    # クールダウン期間が過ぎたらリセット
    if _circuit_breaker_last_open:
        elapsed = (
            datetime.now(timezone.utc) - _circuit_breaker_last_open
        ).total_seconds()
        if elapsed > cooldown_sec:
            _circuit_breaker_failures = 0
            _circuit_breaker_last_open = None
            logger.info("サーキットブレーカ: クールダウン完了、リセット")
            return False

    return True


def _on_ai_failure():
    """AI呼び出し失敗時にサーキットブレーカを更新する。"""
    global _circuit_breaker_failures, _circuit_breaker_last_open
    _circuit_breaker_failures += 1
    threshold = get_config_int("CIRCUIT_BREAKER_THRESHOLD", 10)
    if _circuit_breaker_failures >= threshold:
        _circuit_breaker_last_open = datetime.now(timezone.utc)
        logger.warning(
            f"サーキットブレーカ OPEN: 連続失敗={_circuit_breaker_failures} "
            f"(閾値={threshold})"
        )


def _on_ai_success():
    """AI呼び出し成功時にサーキットブレーカをリセットする。"""
    global _circuit_breaker_failures, _circuit_breaker_last_open
    _circuit_breaker_failures = 0
    _circuit_breaker_last_open = None


def _build_daily_prompt(stock_code: str, market_data: Dict[str, Any]) -> str:
    """
    日次分析用プロンプトを組み立てる。
    状態説明に徹し、売買推奨は行わない（金融安全ルール）。
    """
    price = market_data.get("current_price", "-")
    change_pct = market_data.get("change_pct", "-")
    volume = market_data.get("volume", "-")
    rsi = market_data.get("rsi", "-")
    sma25 = market_data.get("sma25", "-")
    sma75 = market_data.get("sma75", "-")
    trend = market_data.get("trend_label", "-")
    name = market_data.get("name", stock_code)

    return f"""あなたは株式市場の状態を説明するアナリストです。
以下の銘柄データに基づき、現在の市場状態を日本語で簡潔に説明してください。

【絶対禁止】
- 「買い」「売り」「推奨」「エントリー」などの売買を示唆する表現
- 投資判断に直接つながる助言

【銘柄】{name}（{stock_code}）
【現在値】{price}
【前日比】{change_pct}%
【出来高】{volume}
【RSI】{rsi}
【SMA25】{sma25}
【SMA75】{sma75}
【トレンド】{trend}

以下の項目で200〜300字程度にまとめてください：
1. テクニカルの状態（移動平均線の位置関係、RSIの水準、トレンド方向）
2. 出来高の評価（通常比での増減）
3. 注目すべきポイント（サポート/レジスタンス付近かどうか等）

※ 状態の説明に徹し、売買の助言は含めないでください。"""


def _build_intraday_prompt(stock_code: str, market_data: Dict[str, Any]) -> str:
    """
    イントラデイ分析用の軽量プロンプト。
    短文コメント中心（50〜100字程度）。
    """
    price = market_data.get("current_price", "-")
    change_pct = market_data.get("change_pct", "-")
    rsi = market_data.get("rsi", "-")
    trend = market_data.get("trend_label", "-")
    name = market_data.get("name", stock_code)

    return f"""以下の銘柄の直近の状態変化を1〜2文で簡潔に説明してください。

【絶対禁止】売買を示唆する表現

【銘柄】{name}（{stock_code}）
【現在値】{price}（前日比{change_pct}%）
【RSI】{rsi}
【トレンド】{trend}

50〜100字で状態の変化を説明してください。"""


def _gather_market_data(stock_code: str) -> Dict[str, Any]:
    """
    ワーカーが使用する市場データを収集する。
    stock_serviceのデータフェッチャーを活用。
    """
    try:
        from services.data_fetcher import (
            fetch_stock_data,
            fetch_stock_info,
            format_symbol_for_yfinance,
        )
        from utils.analyzer import add_technical_indicators
        from data.stock_name_mapper import STOCK_NAME_MAP
        import pandas as pd

        symbol = format_symbol_for_yfinance(stock_code)
        info = fetch_stock_info(symbol) or {}
        df = fetch_stock_data(symbol, period="3mo", interval="1d")

        result = {
            "name": STOCK_NAME_MAP.get(stock_code, info.get("name", stock_code)),
            "current_price": info.get("current_price", "-"),
            "change_pct": "-",
            "volume": info.get("volume", "-"),
            "rsi": "-",
            "sma25": "-",
            "sma75": "-",
            "trend_label": "-",
        }

        # 変化率
        prev = info.get("previous_close")
        curr = info.get("current_price")
        if prev and curr and prev > 0:
            result["change_pct"] = f"{((curr - prev) / prev) * 100:.2f}"

        # テクニカル指標
        if df is not None and not df.empty:
            df = add_technical_indicators(df, sma_periods=[25, 75])
            last = df.iloc[-1]
            if "RSI" in df.columns and not pd.isna(last.get("RSI")):
                result["rsi"] = f"{last['RSI']:.1f}"
            if "SMA25" in df.columns and not pd.isna(last.get("SMA25")):
                result["sma25"] = f"{last['SMA25']:.0f}"
            if "SMA75" in df.columns and not pd.isna(last.get("SMA75")):
                result["sma75"] = f"{last['SMA75']:.0f}"

            # トレンド判定
            closes = df["close"].dropna()
            if len(closes) > 5:
                from utils.analyzer import get_direction_label

                result["trend_label"] = get_direction_label(
                    closes,
                    positive_label="上昇トレンド",
                    negative_label="下落トレンド",
                    neutral_label="レンジ",
                )

        return result

    except Exception as e:
        logger.error(f"市場データ収集エラー {stock_code}: {e}")
        return {
            "name": stock_code,
            "current_price": "-",
            "change_pct": "-",
            "volume": "-",
            "rsi": "-",
            "sma25": "-",
            "sma75": "-",
            "trend_label": "-",
        }


def _call_ai(prompt: str, model_name: str = "gemini-1.5-flash") -> str:
    """
    AI APIを呼び出してテキストを生成する。
    Gemini → OpenAI のフォールバック付き。
    """
    # まず Gemini を試行
    try:
        from services.ai_client import get_gemini_model

        model = get_gemini_model(model_name)
        if model:
            response = model.generate_content(prompt)
            if response and response.text:
                return response.text.strip()
    except Exception as e:
        logger.warning(f"Gemini API呼び出し失敗: {e}")

    # フォールバック: OpenAI
    try:
        from services.ai_client import get_ai_client

        client = get_ai_client()
        if client:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,  # 低温度（再現性重視）
                max_tokens=500,
            )
            return response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"OpenAI API呼び出し失敗: {e}")

    raise RuntimeError("全てのAI APIの呼び出しに失敗しました")


def generate_analysis(
    stock_code: str,
    analysis_type: str,
) -> Dict[str, Any]:
    """
    指定された銘柄×分析タイプでAI分析テキストを生成する。
    戻り値: {"content_md": str, "model_version": str, "prompt_version": str, "asof_ts": datetime}
    """
    market_data = _gather_market_data(stock_code)

    # 分析タイプに応じたプロンプト
    if analysis_type == "ai_assist_intraday":
        prompt = _build_intraday_prompt(stock_code, market_data)
        prompt_version = "intraday_v1.0"
    else:
        # デフォルトはdaily
        prompt = _build_daily_prompt(stock_code, market_data)
        prompt_version = "daily_v1.0"

    model_name = "gemini-1.5-flash"
    content = _call_ai(prompt, model_name)

    return {
        "content_md": content,
        "model_version": model_name,
        "prompt_version": prompt_version,
        "asof_ts": datetime.now(timezone.utc),
    }


def run_worker_cycle(worker_id: str = None) -> Dict[str, Any]:
    """
    ワーカー1サイクル: ジョブを1件取得→ロック→AI生成→snapshot upsert。
    戻り値: 処理結果の概要dict。
    """
    if worker_id is None:
        worker_id = f"worker-{uuid.uuid4().hex[:8]}"

    # サーキットブレーカチェック
    if _check_circuit_breaker():
        return {"status": "circuit_breaker_open", "message": "AI呼び出し一時停止中"}

    db = SessionLocal()
    try:
        # ジョブ取得
        job = fetch_next_job(worker_id, db)
        if job is None:
            return {"status": "no_job", "message": "処理待ちジョブなし"}

        logger.info(
            f"ワーカー開始: job_id={job.job_id} "
            f"{job.stock_code}/{job.analysis_type} "
            f"priority={job.priority} reason={job.reason}"
        )

        try:
            # AI生成
            result = generate_analysis(job.stock_code, job.analysis_type)

            # TTL取得
            from services.analysis_snapshot_service import get_config_int

            if job.analysis_type == "ai_assist_intraday":
                ttl = get_config_int("TTL_INTRADAY_SEC", 3600, db)
            else:
                ttl = get_config_int("TTL_DAILY_SEC", 86400, db)

            # スナップショットupsert
            upsert_snapshot(
                stock_code=job.stock_code,
                analysis_type=job.analysis_type,
                content_md=result["content_md"],
                asof_ts=result["asof_ts"],
                input_hash=job.desired_input_hash,
                model_version=result["model_version"],
                prompt_version=result["prompt_version"],
                ttl_sec=ttl,
                status="ok",
                db=db,
            )

            # ジョブ完了
            complete_job(job.job_id, db)
            _on_ai_success()

            logger.info(f"ワーカー完了: job_id={job.job_id}")
            return {
                "status": "done",
                "job_id": job.job_id,
                "stock_code": job.stock_code,
                "analysis_type": job.analysis_type,
            }

        except Exception as e:
            # AI生成失敗
            logger.error(f"AI生成エラー job_id={job.job_id}: {e}")
            _on_ai_failure()

            # ジョブを失敗にする
            fail_job(job.job_id, "ai_error", str(e), db)

            # スナップショットのエラー情報だけ更新（前回のcontent_mdは維持）
            update_snapshot_error(
                job.stock_code,
                job.analysis_type,
                "ai_error",
                str(e),
                db,
            )

            return {
                "status": "failed",
                "job_id": job.job_id,
                "error": str(e),
            }

    finally:
        db.close()


def run_worker_loop(max_iterations: int = 100, sleep_sec: float = 1.0):
    """
    ワーカーをループで実行する。
    max_iterations回処理するか、ジョブがなくなるまで繰り返す。
    """
    worker_id = f"worker-{uuid.uuid4().hex[:8]}"
    logger.info(f"ワーカーループ開始: worker_id={worker_id}")

    processed = 0
    for i in range(max_iterations):
        result = run_worker_cycle(worker_id)

        if result["status"] == "no_job":
            logger.info("処理待ちジョブなし。ワーカーループ終了")
            break
        elif result["status"] == "circuit_breaker_open":
            logger.warning("サーキットブレーカ発動中。ワーカーループ終了")
            break
        elif result["status"] == "done":
            processed += 1

        # 連続処理時の負荷軽減
        time.sleep(sleep_sec)

    logger.info(f"ワーカーループ終了: 処理件数={processed}")
    return {"processed": processed, "worker_id": worker_id}
