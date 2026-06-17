"""
ニュースバッチ処理サービス
ニュース取得 → DB保存 → AI対象フィルタ → AI要約 → 結果保存
の一連処理をバックグラウンドで実行する。
"""

import logging
import json
import threading
import time
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from database import SessionLocal
from models.news_article import NewsArticle
from models.news_ai_summary import NewsAiSummary
from models.news_related_ticker import NewsRelatedTicker
from services.data_fetcher import fetch_news
from services.news_text_preprocessor import preprocess_news_text, compute_text_hash
from services.news_ai_filter import filter_articles_for_ai
from services.news_ticker_extractor import extract_and_save_tickers

logger = logging.getLogger(__name__)

# ================================================================
# 定数
# ================================================================

# ニュース取得対象のティッカー（指数・為替）
NEWS_TICKERS = ["^N225", "^DJI", "JPY=X"]

# ティッカーごとの取得上限
NEWS_PER_TICKER = 5

# AI要約に使用するモデル名
AI_MODEL_NAME = "gemini-flash-latest"

# プロンプトバージョン（変更時に再分析対象になる）
PROMPT_VERSION = "v1.0"

# AI要約の最大再試行回数
MAX_RETRY_COUNT = 3

# バッチ実行間隔（秒）
BATCH_INTERVAL_SEC = 15 * 60  # 15分


# ================================================================
# Step 1: ニュース取得 → DB保存
# ================================================================


def fetch_news_to_db(db: Session) -> List[NewsArticle]:
    """
    yfinanceからニュースを取得し、DBに保存する。
    URLで重複排除し、新規記事のみ挿入する。

    Returns:
        新規挿入された記事のリスト
    """
    import concurrent.futures

    all_raw_news = []
    seen_links = set()

    # 並列でニュース取得
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(fetch_news, ticker, limit=NEWS_PER_TICKER): ticker
            for ticker in NEWS_TICKERS
        }
        for future in concurrent.futures.as_completed(futures):
            ticker = futures[future]
            try:
                items = future.result()
                for item in items:
                    link = item.get("link")
                    if link and link not in seen_links:
                        seen_links.add(link)
                        item["_source_ticker"] = ticker
                        all_raw_news.append(item)
            except Exception as e:
                logger.error(f"ニュース取得エラー ({ticker}): {e}")

    logger.info(f"外部ニュース取得完了: {len(all_raw_news)}件（重複排除済み）")

    # DB保存（重複排除: URLで判定）
    new_articles = []
    for item in all_raw_news:
        url = item.get("link", "")
        if not url:
            continue

        # URL重複チェック
        existing = db.query(NewsArticle).filter(NewsArticle.url == url).first()

        if existing:
            # 既存記事: 本文ハッシュが変わった場合は更新
            raw_text = item.get("summary", "")
            new_hash = compute_text_hash(raw_text)
            if new_hash != existing.raw_text_hash and raw_text:
                existing.raw_text = raw_text
                existing.raw_text_hash = new_hash
                # 本文更新されたので再分析対象にする（成功済みの場合のみ）
                if existing.ai_status == "summarized":
                    existing.ai_status = "queued"
                    logger.info(f"本文更新を検出、再分析対象に: {existing.title[:50]}")
            continue

        # 新規記事: 挿入
        raw_text = item.get("summary", "")
        text_hash = compute_text_hash(raw_text)

        article = NewsArticle(
            source_name=item.get("_source_ticker", "-"),
            source_article_id="",
            url=url,
            title=item.get("title", "-"),
            publisher=item.get("publisher", "-"),
            published_at=item.get("published_at"),
            raw_text=raw_text,
            raw_text_hash=text_hash,
            ai_status="fetched",
            is_ai_target=False,
            retry_count=0,
        )
        db.add(article)
        new_articles.append(article)

    db.commit()
    logger.info(f"DB保存完了: 新規{len(new_articles)}件")
    return new_articles


# ================================================================
# Step 2: AI対象フィルタ適用
# ================================================================


def apply_ai_filter(db: Session) -> None:
    """
    fetched状態の記事に対してAI対象フィルタを適用する。
    """
    articles = db.query(NewsArticle).filter(NewsArticle.ai_status == "fetched").all()

    if not articles:
        logger.info("フィルタ対象の新規記事なし")
        return

    filter_articles_for_ai(db, articles)
    db.commit()


# ================================================================
# Step 3: 1記事ずつAI要約実行
# ================================================================


def _build_single_article_prompt(preprocessed_text: str) -> str:
    """
    1記事用のAI要約プロンプトを構築する。
    短い固定JSONで応答させる。
    """
    return f"""以下のニュース記事を分析し、必ず以下のJSON形式のみで回答してください。
JSON以外の文章は一切含めないでください。

{preprocessed_text}

出力JSON形式（厳守）:
{{
  "summary": "80文字以内で簡潔に日本語で要約",
  "translated_title": "記事タイトルの自然な日本語訳（元が日本語ならそのまま）",
  "sentiment": "positive または negative または neutral",
  "reason": "50文字以内でセンチメントの理由を日本語で説明",
  "related_companies": ["関連企業名を最大3つ"],
  "related_tickers": ["証券コードを最大3つ"]
}}"""


def analyze_single_article(article: NewsArticle, db: Session) -> bool:
    """
    1記事に対してAI要約を実行し、結果をDBに保存する。

    Returns:
        True: 要約成功, False: 要約失敗
    """
    import google.generativeai as genai
    from services.ai_client import get_gemini_model

    # 本文前処理（トークン節約）
    preprocessed = preprocess_news_text(
        title=article.title or "", raw_text=article.raw_text or ""
    )
    input_hash = compute_text_hash(preprocessed)

    # 既存の要約で同一input_hash + 同一prompt_versionがあればスキップ
    existing_summary = (
        db.query(NewsAiSummary)
        .filter(
            NewsAiSummary.news_article_id == article.id,
            NewsAiSummary.input_hash == input_hash,
            NewsAiSummary.prompt_version == PROMPT_VERSION,
            NewsAiSummary.analysis_status == "success",
        )
        .first()
    )

    if existing_summary:
        logger.info(f"既存の要約あり、スキップ: 記事ID={article.id}")
        article.ai_status = "summarized"
        return True

    # ステータス更新: 分析中
    article.ai_status = "processing"
    db.commit()

    # プロンプト構築
    prompt = _build_single_article_prompt(preprocessed)

    try:
        # Gemini APIで要約
        model = get_gemini_model(AI_MODEL_NAME)
        if not model:
            raise RuntimeError("Gemini APIキーが設定されていません")

        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json", temperature=0.2
            ),
        )
        content = response.text

        # JSONパース（不正JSONでも落ちないように）
        try:
            data = json.loads(content)
        except json.JSONDecodeError as je:
            logger.error(f"AI応答のJSONパースエラー: 記事ID={article.id}, error={je}")
            raise ValueError(f"不正なJSON応答: {content[:200]}")

        # 必須フィールドの検証
        summary_text = data.get("summary", "")
        if not summary_text:
            raise ValueError("AI応答にsummaryが含まれていません")

        # 要約結果をDBに保存
        ai_summary = NewsAiSummary(
            news_article_id=article.id,
            model_name=AI_MODEL_NAME,
            prompt_version=PROMPT_VERSION,
            input_hash=input_hash,
            summary=summary_text[:200],  # 安全のため文字数制限
            translated_title=data.get("translated_title", "")[:500],
            sentiment=data.get("sentiment", "neutral"),
            reason=data.get("reason", "")[:200],
            analysis_status="success",
            analyzed_at=datetime.now(timezone.utc),
        )
        db.add(ai_summary)

        # AI応答から関連銘柄も保存（AIベース抽出）
        related_tickers = data.get("related_tickers", [])
        related_companies = data.get("related_companies", [])
        for i, ticker_code in enumerate(related_tickers[:3]):
            company_name = related_companies[i] if i < len(related_companies) else "-"
            existing_ticker = (
                db.query(NewsRelatedTicker)
                .filter(
                    NewsRelatedTicker.news_article_id == article.id,
                    NewsRelatedTicker.ticker_code == str(ticker_code),
                    NewsRelatedTicker.extraction_type == "ai",
                )
                .first()
            )
            if not existing_ticker:
                # センチメントに基づくimpact_type判定
                sentiment_val = data.get("sentiment", "neutral")
                if sentiment_val == "positive":
                    impact = "positive"
                elif sentiment_val == "negative":
                    impact = "negative"
                else:
                    impact = "positive"  # neutral の場合はデフォルトpositive
                db.add(
                    NewsRelatedTicker(
                        news_article_id=article.id,
                        ticker_code=str(ticker_code),
                        company_name=str(company_name),
                        impact_type=impact,
                        confidence=0.8,
                        extraction_type="ai",
                        reason=data.get("reason", "")[:200],
                    )
                )

        # ステータス更新: 要約成功
        article.ai_status = "summarized"
        article.last_analyzed_at = datetime.now(timezone.utc)
        db.commit()

        logger.info(f"AI要約成功: 記事ID={article.id}, タイトル={article.title[:40]}")
        return True

    except Exception as e:
        logger.error(f"AI要約失敗: 記事ID={article.id}, error={e}")
        article.ai_status = "failed"
        article.retry_count += 1
        article.last_error_message = str(e)[:500]
        db.commit()
        return False


def run_ai_summaries(db: Session) -> dict:
    """
    queued状態の記事を1件ずつAI要約する。
    再試行上限未満のfailed記事も対象に含む。

    Returns:
        {"success": int, "failed": int, "skipped": int}
    """
    # 対象記事を取得: queued状態 + 再試行可能なfailed状態
    articles = (
        db.query(NewsArticle)
        .filter(
            (NewsArticle.ai_status == "queued")
            | (
                (NewsArticle.ai_status == "failed")
                & (NewsArticle.retry_count < MAX_RETRY_COUNT)
            )
        )
        .order_by(NewsArticle.published_at.desc())
        .all()
    )

    if not articles:
        logger.info("AI要約対象の記事なし")
        return {"success": 0, "failed": 0, "skipped": 0}

    logger.info(f"AI要約開始: {len(articles)}件")

    results = {"success": 0, "failed": 0, "skipped": 0}

    for article in articles:
        try:
            success = analyze_single_article(article, db)
            if success:
                results["success"] += 1
            else:
                results["failed"] += 1
        except Exception as e:
            logger.error(f"予期しないエラー: 記事ID={article.id}, error={e}")
            results["failed"] += 1

        # API Rate Limit対策: 1記事ごとに少し待機
        time.sleep(1)

    logger.info(f"AI要約完了: {results}")
    return results


# ================================================================
# Step 4: ルールベース銘柄抽出
# ================================================================


def run_ticker_extraction(db: Session) -> int:
    """
    要約済み以外の新規記事に対してルールベース銘柄抽出を実行する。

    Returns:
        抽出処理した記事数
    """
    # ルールベース抽出がまだの記事（created_atが新しい順）
    articles = (
        db.query(NewsArticle)
        .filter(NewsArticle.ai_status.in_(["fetched", "queued", "summarized"]))
        .all()
    )

    count = 0
    for article in articles:
        # 既にルールベース抽出済みかチェック
        existing_rule = (
            db.query(NewsRelatedTicker)
            .filter(
                NewsRelatedTicker.news_article_id == article.id,
                NewsRelatedTicker.extraction_type == "rule",
            )
            .first()
        )
        if existing_rule:
            continue

        extract_and_save_tickers(
            db=db,
            article_id=article.id,
            title=article.title or "",
            raw_text=article.raw_text or "",
        )
        count += 1

    db.commit()
    logger.info(f"ルールベース銘柄抽出完了: {count}件処理")
    return count


# ================================================================
# オーケストレータ: 全処理を順次実行
# ================================================================


def run_full_batch() -> dict:
    """
    ニュース取得からAI要約まで一連のバッチ処理を実行する。
    各ステップを順次実行し、結果をまとめて返す。
    """
    logger.info("=" * 60)
    logger.info("ニュースバッチ処理開始")
    logger.info("=" * 60)

    db = SessionLocal()
    results = {
        "fetch_count": 0,
        "ai_results": {"success": 0, "failed": 0, "skipped": 0},
        "ticker_count": 0,
        "error": None,
    }

    try:
        # Step 1: ニュース取得 → DB保存
        logger.info("[Step 1/4] ニュース取得・DB保存")
        new_articles = fetch_news_to_db(db)
        results["fetch_count"] = len(new_articles)

        # Step 2: AI対象フィルタ
        logger.info("[Step 2/4] AI対象フィルタ適用")
        apply_ai_filter(db)

        # Step 3: ルールベース銘柄抽出
        logger.info("[Step 3/4] ルールベース銘柄抽出")
        results["ticker_count"] = run_ticker_extraction(db)

        # Step 4: AI要約
        logger.info("[Step 4/4] AI要約実行")
        results["ai_results"] = run_ai_summaries(db)

    except Exception as e:
        logger.error(f"バッチ処理エラー: {e}")
        results["error"] = str(e)
    finally:
        db.close()

    logger.info(f"ニュースバッチ処理完了: {results}")
    logger.info("=" * 60)
    return results


# ================================================================
# スケジューラ: 定期実行
# ================================================================

_scheduler_running = False


def start_news_scheduler():
    """
    ニュースバッチ処理を定期実行するスケジューラを起動する。
    バックグラウンドスレッドで動作する。
    """
    global _scheduler_running
    if _scheduler_running:
        logger.warning("ニューススケジューラは既に起動中")
        return

    _scheduler_running = True

    def _scheduler_loop():
        global _scheduler_running
        logger.info(f"ニューススケジューラ起動: {BATCH_INTERVAL_SEC}秒間隔")

        # 起動直後に初回実行（少し待ってからDB接続）
        time.sleep(10)
        try:
            run_full_batch()
        except Exception as e:
            logger.error(f"初回バッチ実行エラー: {e}")

        # 定期実行ループ
        while _scheduler_running:
            time.sleep(BATCH_INTERVAL_SEC)
            try:
                run_full_batch()
            except Exception as e:
                logger.error(f"定期バッチ実行エラー: {e}")

    thread = threading.Thread(
        target=_scheduler_loop, daemon=True, name="news-scheduler"
    )
    thread.start()
    logger.info("ニューススケジューラ スレッド起動完了")


def stop_news_scheduler():
    """
    ニューススケジューラを停止する。
    """
    global _scheduler_running
    _scheduler_running = False
    logger.info("ニューススケジューラ停止要求")
