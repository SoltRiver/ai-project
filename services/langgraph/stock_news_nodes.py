"""
LangGraph: Stock News Nodes
"""

import logging

from ai.chains.news_summarizer import summarize_news_batch_async
from services.data_fetcher import fetch_news
from services.langgraph.stock_news_state import StockNewsState

logger = logging.getLogger(__name__)


async def fetch_news_node(state: StockNewsState) -> StockNewsState:
    """
    指定された銘柄コードのニュースを取得するノード。
    """
    logger.info(f"fetch_news_node started for {state.get('stock_code')}")
    try:
        stock_code = state["stock_code"]
        # yfinanceベースの既存処理を呼び出し
        news_items = fetch_news(stock_code, limit=5)

        if not news_items:
            logger.warning(
                "No news found for %s. Using fallback dummy data.", stock_code
            )
            # 既存ニュースが取れない場合は仮データを入れる（指示に基づくフォールバック）
            news_items = [
                {
                    "title": f"【仮データ】{stock_code}の最新業績見通し",
                    "publisher": "テスト通信",
                    "link": "#",
                    "published_at": "今日",
                    "summary": (
                        f"{stock_code}は新規事業への投資を拡大する方針を発表した。"
                        "市場はこれを好感して買いが集まっている。"
                    ),
                }
            ]

        return {"news_items": news_items}
    except Exception as e:
        logger.error(f"Error in fetch_news_node: {e}")
        return {"error": f"ニュース取得に失敗しました: {e}"}


async def summarize_news_node(state: StockNewsState) -> StockNewsState:
    """
    取得したニュースをLLMで要約・センチメント判定するノード。
    """
    logger.info("summarize_news_node started")
    if "error" in state:
        return state

    news_items = state.get("news_items", [])
    if not news_items:
        return {"error": "要約対象のニュースがありません"}

    language = state.get("language", "日本語")

    # クォータ制限対策として、googleが完全に失敗した場合はopenaiへ自動フォールバックする
    providers = ["google", "openai"]
    batch_results = None
    last_error = None

    for provider in providers:
        try:
            logger.info(f"Attempting news summary with provider: {provider}")
            batch_results = await summarize_news_batch_async(
                articles=news_items, provider=provider, language=language
            )
            # 全件エラーでなければ成功とみなす
            all_failed = all(
                any(
                    msg in r.get("summarized_content", "")
                    for msg in [
                        "Failed to generate summary.",
                        "要約の生成に失敗しました。",
                        "現在、AI要約サービスの利用が集中しており、一時的に要約を生成できません。",
                        "AI summary is temporarily unavailable due to high traffic.",
                    ]
                )
                for r in batch_results
            )
            if not all_failed:
                logger.info(f"Successfully summarized news with provider: {provider}")
                break
            else:
                logger.warning(
                    f"All articles failed to summarize with provider: {provider}"
                )
        except Exception as e:
            logger.error(f"Provider {provider} failed with error: {e}")
            last_error = e

    if batch_results is None:
        return {
            "error": f"要約処理中にエラーが発生しました: {last_error or 'No provider succeeded'}"
        }

    summaries = []
    for idx, result in enumerate(batch_results):
        # 元記事データと要約結果をマージして保存
        summary_data = {"original": news_items[idx], "ai_result": result}
        summaries.append(summary_data)

    if not summaries:
        return {"error": "ニュースの要約に全て失敗しました"}

    return {"summaries": summaries}


async def classify_sentiment_node(state: StockNewsState) -> StockNewsState:
    """
    センチメントを検証するノード。
    LLMが既に出力している 'positive', 'negative', 'neutral' が正しいフォーマットか
    ルールベースで確認・修正する（無駄なLLM呼び出しを避けるため）。
    """
    logger.info("classify_sentiment_node started")
    if "error" in state:
        return state

    summaries = state.get("summaries", [])
    valid_sentiments = ["positive", "negative", "neutral"]

    for item in summaries:
        result = item.get("ai_result", {})
        sentiment = str(result.get("sentiment", "")).lower()

        # フォーマット外の場合は neutral にフォールバック
        if sentiment not in valid_sentiments:
            logger.warning(
                f"Invalid sentiment '{sentiment}' detected. Falling back to neutral."
            )
            result["sentiment"] = "neutral"

    return {"summaries": summaries}


async def build_response_node(state: StockNewsState) -> StockNewsState:
    """
    画面表示用にデータを整形するノード。
    """
    logger.info("build_response_node started")
    if "error" in state:
        return state

    summaries = state.get("summaries", [])

    # テンプレートに渡しやすい形式に整形
    formatted_items = []
    for item in summaries:
        orig = item["original"]
        ai = item["ai_result"]

        formatted_items.append(
            {
                "title": ai.get("translated_title", orig.get("title")),
                "original_url": orig.get("link", "#"),
                "publisher": orig.get("publisher", "-"),
                "published_at": orig.get("published_at", ""),
                "summary": ai.get("summarized_content", ""),
                "sentiment": ai.get("sentiment", "neutral"),
                "sentiment_reason": ai.get("sentiment_reason", ""),
                "impacted_stocks": ai.get("impacted_stocks", []),
            }
        )

    # [TODO] 将来的なDB保存の差し込み口
    # 例: save_summaries_to_db(state["stock_code"], formatted_items)

    response = {"stock_code": state.get("stock_code"), "items": formatted_items}

    return {"response": response}
