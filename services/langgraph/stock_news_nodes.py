"""
LangGraph: Stock News Nodes
"""

import logging

from pydantic import ValidationError

from ai.chains.news_summarizer import summarize_news_batch_async
from services.data_fetcher import fetch_news
from services.langgraph.stock_news_schemas import (AISummaryResult,
                                                   FormattedNewsItem, NewsItem,
                                                   NewsSummaryItem,
                                                   StockNewsInput,
                                                   StockNewsResponse)
from services.langgraph.stock_news_state import StockNewsState

logger = logging.getLogger(__name__)


async def fetch_news_node(state: StockNewsState) -> StockNewsState:
    """
    指定された銘柄コードのニュースを取得するノード。
    """
    logger.info(f"fetch_news_node started for {state.get('stock_code')}")
    try:
        # 入力パラメータのバリデーションチェック
        try:
            input_data = StockNewsInput(
                stock_code=state.get("stock_code", ""),
                language=state.get("language", "日本語"),
            )
            stock_code = input_data.stock_code
        except ValidationError as e:
            logger.error(f"Input validation failed: {e}")
            return {"error": f"入力パラメータが不正です: {e}"}

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

        # 取得したニュースデータのバリデーションチェック
        validated_news_items = []
        for item in news_items:
            try:
                validated_item = NewsItem(**item)
                validated_news_items.append(validated_item.model_dump())
            except ValidationError as e:
                logger.warning(f"NewsItem validation failed for {item}: {e}")
                # 個別アイテムのパース失敗はログ出力し、スキップして堅牢性を確保

        if not validated_news_items:
            logger.error("All news items failed validation.")
            return {
                "error": "取得したニュースデータのバリデーションにすべて失敗しました。"
            }

        return {"news_items": validated_news_items}
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

    # 事前に格納されているニュースデータのバリデーション再チェック
    validated_news_items = []
    for item in news_items:
        try:
            validated_news_items.append(NewsItem(**item).model_dump())
        except ValidationError as e:
            logger.warning(f"Pre-validation of news_items failed: {e}")

    if not validated_news_items:
        return {"error": "有効な要約対象のニュースがありません"}

    language = state.get("language", "日本語")

    # クォータ制限対策として、googleが完全に失敗した場合はopenaiへ自動フォールバックする
    providers = ["google", "openai"]
    batch_results = None
    last_error = None

    for provider in providers:
        try:
            logger.info(f"Attempting news summary with provider: {provider}")
            batch_results = await summarize_news_batch_async(
                articles=validated_news_items, provider=provider, language=language
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
        try:
            # 元記事とAI判定結果をマージし、Pydanticでバリデーション
            # もし LLM 出力が一部欠落していても、Pydanticがデフォルト値 (例: "-") を補う
            summary_item = NewsSummaryItem(
                original=NewsItem(**validated_news_items[idx]),
                ai_result=AISummaryResult(**result),
            )
            summaries.append(summary_item.model_dump())
        except ValidationError as e:
            logger.warning(f"NewsSummaryItem validation failed at index {idx}: {e}")
            # エラー発生時はログに記録し、一部の失敗記事はスキップ

    if not summaries:
        return {"error": "ニュースの要約に全て失敗しました（バリデーションエラー）"}

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

    validated_summaries = []
    for item in summaries:
        try:
            # Pydanticを用いて一度パースし、整合性を保つ
            summary_item = NewsSummaryItem(**item)
            original = summary_item.original
            ai_result = summary_item.ai_result

            sentiment = ai_result.sentiment.strip().lower()

            # フォーマット外の場合は neutral にフォールバック
            if sentiment not in valid_sentiments:
                logger.warning(
                    f"Invalid sentiment '{sentiment}' detected. "
                    "Falling back to neutral."
                )
                ai_result.sentiment = "neutral"

            # 補正後の値で再度モデル化して格納
            validated_summaries.append(
                NewsSummaryItem(original=original, ai_result=ai_result).model_dump()
            )
        except ValidationError as e:
            logger.warning(
                f"Validation failed in sentiment node, attempting recovery: {e}"
            )
            # 万が一無効なデータ構造だった場合、フォールバック値で再生成して救済
            try:
                orig_data = item.get("original", {})
                ai_data = item.get("ai_result", {})
                recovered = NewsSummaryItem(
                    original=NewsItem(
                        title=orig_data.get("title", "-"),
                        publisher=orig_data.get("publisher", "-"),
                        link=orig_data.get("link", "#"),
                        published_at=orig_data.get("published_at", ""),
                        summary=orig_data.get("summary", "-"),
                    ),
                    ai_result=AISummaryResult(
                        translated_title=ai_data.get("translated_title"),
                        summarized_content=ai_data.get("summarized_content", "-"),
                        sentiment="neutral",
                        sentiment_reason=ai_data.get("sentiment_reason", "-"),
                        impacted_stocks=ai_data.get("impacted_stocks", []),
                    ),
                )
                validated_summaries.append(recovered.model_dump())
            except Exception as recover_err:
                logger.error(f"Recovery failed in sentiment node: {recover_err}")

    return {"summaries": validated_summaries}


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
        try:
            # 事前に NewsSummaryItem としてパースできるかチェック
            summary_item = NewsSummaryItem(**item)
            orig = summary_item.original
            ai = summary_item.ai_result

            # 画面表示用の個別アイテムを作成しバリデーションを実行
            formatted_item = FormattedNewsItem(
                title=ai.translated_title or orig.title,
                original_url=orig.link,
                publisher=orig.publisher,
                published_at=orig.published_at,
                summary=ai.summarized_content,
                sentiment=ai.sentiment,
                sentiment_reason=ai.sentiment_reason,
                impacted_stocks=ai.impacted_stocks,
            )
            formatted_items.append(formatted_item.model_dump())
        except ValidationError as e:
            logger.warning(f"FormattedNewsItem validation failed: {e}")
            # パースに失敗した記事は画面表示から除外、またはログ記録してスキップ

    # 最終的なレスポンスデータを作成
    response_data = {
        "stock_code": state.get("stock_code", ""),
        "items": formatted_items,
    }

    try:
        # レスポンス全体の構造がスキーマに合致しているか最終バリデーション
        validated_response = StockNewsResponse(**response_data)
        response = validated_response.model_dump()
    except ValidationError as e:
        logger.error(f"StockNewsResponse validation failed: {e}")
        return {"error": f"レスポンス生成時のバリデーションエラー: {e}"}

    # [TODO] 将来的なDB保存の差し込み口
    # 例: save_summaries_to_db(state["stock_code"], formatted_items)

    return {"response": response}
