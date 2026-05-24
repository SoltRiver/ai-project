"""
LangGraph: Stock News Nodes
"""

import logging
from typing import Dict, Any

from services.langgraph.stock_news_state import StockNewsState
from services.data_fetcher import fetch_news
from ai.chains.news_summarizer import summarize_news_article

logger = logging.getLogger(__name__)

def fetch_news_node(state: StockNewsState) -> StockNewsState:
    """
    指定された銘柄コードのニュースを取得するノード。
    """
    logger.info(f"fetch_news_node started for {state.get('stock_code')}")
    try:
        stock_code = state["stock_code"]
        # yfinanceベースの既存処理を呼び出し
        news_items = fetch_news(stock_code, limit=5)
        
        if not news_items:
            logger.warning(f"No news found for {stock_code}. Using dummy data as fallback.")
            # 既存ニュースが取れない場合は仮データを入れる（指示に基づくフォールバック）
            news_items = [
                {
                    "title": f"【仮データ】{stock_code}の最新業績見通し",
                    "publisher": "テスト通信",
                    "link": "#",
                    "published_at": "今日",
                    "summary": f"{stock_code}は新規事業への投資を拡大する方針を発表した。市場はこれを好感して買いが集まっている。"
                }
            ]

        return {"news_items": news_items}
    except Exception as e:
        logger.error(f"Error in fetch_news_node: {e}")
        return {"error": f"ニュース取得に失敗しました: {e}"}


def summarize_news_node(state: StockNewsState) -> StockNewsState:
    """
    取得したニュースをLLMで要約・センチメント判定するノード。
    """
    logger.info(f"summarize_news_node started")
    if "error" in state:
        return state

    news_items = state.get("news_items", [])
    if not news_items:
        return {"error": "要約対象のニュースがありません"}

    summaries = []
    for item in news_items:
        try:
            # 既存の LangChain チェーン（Pydanticバリデーション付き）を利用
            # 内部で services.ai.llm_client を利用するよう変更済み
            # 注: デフォルトでは gemini-2.0-flash が使われる
            result = summarize_news_article(
                title=item.get("title", ""),
                body=item.get("summary", ""),
                publisher=item.get("publisher", ""),
                provider="google" # Geminiを利用
            )
            
            # 元記事データと要約結果をマージして保存
            summary_data = {
                "original": item,
                "ai_result": result
            }
            summaries.append(summary_data)
            
        except Exception as e:
            logger.error(f"Error summarizing news '{item.get('title')}': {e}")
            # エラーの場合はスキップして次へ
            continue

    if not summaries:
        return {"error": "ニュースの要約に全て失敗しました"}

    return {"summaries": summaries}


def classify_sentiment_node(state: StockNewsState) -> StockNewsState:
    """
    センチメントを検証するノード。
    LLMが既に出力している 'positive', 'negative', 'neutral' が正しいフォーマットか
    ルールベースで確認・修正する（無駄なLLM呼び出しを避けるため）。
    """
    logger.info(f"classify_sentiment_node started")
    if "error" in state:
        return state

    summaries = state.get("summaries", [])
    valid_sentiments = ["positive", "negative", "neutral"]

    for item in summaries:
        result = item.get("ai_result", {})
        sentiment = str(result.get("sentiment", "")).lower()
        
        # フォーマット外の場合は neutral にフォールバック
        if sentiment not in valid_sentiments:
            logger.warning(f"Invalid sentiment '{sentiment}' detected. Falling back to neutral.")
            result["sentiment"] = "neutral"

    return {"summaries": summaries}


def build_response_node(state: StockNewsState) -> StockNewsState:
    """
    画面表示用にデータを整形するノード。
    """
    logger.info(f"build_response_node started")
    if "error" in state:
        return state

    summaries = state.get("summaries", [])
    
    # テンプレートに渡しやすい形式に整形
    formatted_items = []
    for item in summaries:
        orig = item["original"]
        ai = item["ai_result"]
        
        formatted_items.append({
            "title": ai.get("translated_title", orig.get("title")),
            "original_url": orig.get("link", "#"),
            "publisher": orig.get("publisher", "-"),
            "published_at": orig.get("published_at", ""),
            "summary": ai.get("summarized_content", ""),
            "sentiment": ai.get("sentiment", "neutral"),
            "sentiment_reason": ai.get("sentiment_reason", ""),
            "impacted_stocks": ai.get("impacted_stocks", [])
        })

    # [TODO] 将来的なDB保存の差し込み口
    # 例: save_summaries_to_db(state["stock_code"], formatted_items)

    response = {
        "stock_code": state.get("stock_code"),
        "items": formatted_items
    }

    return {"response": response}
