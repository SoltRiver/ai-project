"""
ニュース要約チェーン（LangChain版）

金融ニュース記事を受け取り、以下を生成する単発処理チェーン:
- 日本語タイトル翻訳
- 初心者向け要約（80文字以内目標）
- センチメント判定（positive / negative / neutral）
- センチメント判定理由
- 影響銘柄リスト（銘柄名・影響タイプ・理由）

既存の ai_client.py (analyze_news_impact_batch) と同等の出力を
LangChain の PromptTemplate + ChatModel + OutputParser で実現する。
"""

import logging
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

# LangChain コンポーネント
from langchain_core.output_parsers import JsonOutputParser

# プロンプト・出力スキーマ（ai/prompts に分離済み）
from ai.prompts.news_prompts import NewsSummaryOutput, build_news_summary_prompt

# LLMクライアント
from services.ai.llm_client import get_chat_model

logger = logging.getLogger(__name__)

# .envファイルから環境変数をロード
load_dotenv()


# ====================================================================
# チェーン構築
# ====================================================================


def _build_news_summary_chain(
    provider: str = "openai", model_name: Optional[str] = None
):
    """
    ニュース要約チェーンを構築する。

    構成:
        入力 → PromptTemplate → ChatModel → JsonOutputParser → 出力

    Args:
        provider: LLMプロバイダ名
        model_name: モデル名（省略時はデフォルト）

    Returns:
        実行可能なLCELチェーン
    """
    # 出力パーサー（Pydanticスキーマによるバリデーション付き）
    parser = JsonOutputParser(pydantic_object=NewsSummaryOutput)

    # プロンプトテンプレート構築（ai/prompts から取得）
    prompt = build_news_summary_prompt().partial(
        format_instructions=parser.get_format_instructions()
    )

    # ChatModel取得
    llm = get_chat_model(provider=provider, model_name=model_name)

    # LCEL（LangChain Expression Language）でチェーンを構築
    # 入力dict → プロンプト → LLM → JSON解析 の単純なパイプライン
    chain = prompt | llm | parser

    return chain


# ====================================================================
# 公開API: 単発記事の要約
# ====================================================================


def summarize_news_article(
    title: str,
    body: str,
    publisher: str = "-",
    provider: str = "openai",
    model_name: Optional[str] = None,
    language: str = "日本語",
) -> Dict[str, Any]:
    """
    単一のニュース記事を要約する。

    既存の ai_client.analyze_news_impact_batch と同等の出力を
    LangChainチェーンで生成する単発処理。

    Args:
        title: 記事タイトル
        body: 記事本文（サマリー含む）
        publisher: 配信元名
        provider: LLMプロバイダ ("openai" or "google")
        model_name: 使用するモデル名（省略時はデフォルト）
        language: 出力言語 (例: "日本語", "English")

    Returns:
        要約結果の辞書:
        {
            "translated_title": str,
            "summarized_content": str,
            "sentiment": str,
            "sentiment_reason": str,
            "impacted_stocks": [
                {"name": str, "impact_type": str, "reason": str},
                ...
            ]
        }

    Raises:
        ValueError: APIキー未設定時
        Exception: LLM呼び出しエラー時
    """
    logger.info(
        f"ニュース要約開始: provider={provider}, language={language}, title='{title[:50]}...'"
    )

    chain = _build_news_summary_chain(provider=provider, model_name=model_name)

    # チェーン実行（単発呼び出し）
    result = chain.invoke(
        {
            "title": title or "-",
            "publisher": publisher or "-",
            "body": body or "-",
            "language": language,
        }
    )

    logger.info(f"ニュース要約完了: sentiment={result.get('sentiment', '-')}")
    return result


async def summarize_news_article_async(
    title: str,
    body: str,
    publisher: str = "-",
    provider: str = "openai",
    model_name: Optional[str] = None,
    language: str = "日本語",
) -> Dict[str, Any]:
    """
    単一のニュース記事を非同期で要約する。
    """
    logger.info(
        f"ニュース非同期要約開始: {provider=}, {language=}, title='{title[:40]}...'"
    )

    chain = _build_news_summary_chain(provider=provider, model_name=model_name)

    # チェーン実行（非同期呼び出し）
    result = await chain.ainvoke(
        {
            "title": title or "-",
            "publisher": publisher or "-",
            "body": body or "-",
            "language": language,
        }
    )

    logger.info(f"ニュース非同期要約完了: sentiment={result.get('sentiment', '-')}")
    return result


# ====================================================================
# 公開API: バッチ記事の要約
# ====================================================================


def summarize_news_batch(
    articles: List[Dict[str, Any]],
    provider: str = "openai",
    model_name: Optional[str] = None,
    language: str = "日本語",
) -> List[Dict[str, Any]]:
    """
    複数のニュース記事をバッチで要約する。

    各記事を順次処理し、エラーが発生した記事はスキップして
    処理を継続する。

    Args:
        articles: 記事辞書のリスト。各辞書には以下のキーが必要:
            - title: 記事タイトル
            - body or summary or raw_text: 記事本文
            - publisher: 配信元名（省略可）
        provider: LLMプロバイダ
        model_name: モデル名
        language: 出力言語 (例: "日本語", "English")

    Returns:
        要約結果のリスト。各要素にはsummarize_news_articleの出力に加え、
        元記事のインデックス "id" が付与される。
    """
    if not articles:
        return []

    logger.info(
        f"ニュースバッチ要約開始: {len(articles)}件, provider={provider}, language={language}"
    )

    # チェーンを一度だけ構築（同じモデルを使い回す）
    chain = _build_news_summary_chain(provider=provider, model_name=model_name)

    results = []
    success_count = 0
    error_count = 0

    for idx, article in enumerate(articles):
        # 記事本文の取得（複数のキー名に対応）
        body = (
            article.get("body")
            or article.get("summary")
            or article.get("raw_text")
            or "-"
        )

        try:
            result = chain.invoke(
                {
                    "title": article.get("title", "-"),
                    "publisher": article.get("publisher", "-"),
                    "body": body,
                    "language": language,
                }
            )

            # 元記事のインデックスを付与
            result["id"] = idx
            results.append(result)
            success_count += 1

        except Exception as e:
            logger.warning(f"記事[{idx}]の要約でエラー: {type(e).__name__}: {e}")
            error_count += 1

            if "RateLimitError" in str(type(e).__name__) or "429" in str(e):
                fail_content = (
                    "現在、AI要約サービスの利用が集中しており、一時的に要約を生成できません。"
                    if language == "日本語"
                    else (
                        "AI summary is temporarily unavailable due to "
                        "high traffic."
                    )
                )
            else:
                fail_content = (
                    "要約の生成に失敗しました。"
                    if language == "日本語"
                    else "Failed to generate summary."
                )
            # エラー時はフォールバック結果を返す
            results.append(
                {
                    "id": idx,
                    "translated_title": article.get("title", "-"),
                    "summarized_content": fail_content,
                    "sentiment": "neutral",
                    "sentiment_reason": f"処理エラー: {type(e).__name__}",
                    "impacted_stocks": [],
                }
            )

    logger.info(
        f"ニュースバッチ要約完了: 成功={success_count}件, エラー={error_count}件"
    )
    return results


async def summarize_news_batch_async(
    articles: List[Dict[str, Any]],
    provider: str = "openai",
    model_name: Optional[str] = None,
    language: str = "日本語",
) -> List[Dict[str, Any]]:
    """
    複数のニュース記事を非同期に並行処理で要約する。
    """
    if not articles:
        return []

    logger.info(
        f"ニュースバッチ非同期要約開始: {len(articles)}件, provider={provider}, language={language}"
    )

    # チェーンを一度だけ構築
    chain = _build_news_summary_chain(provider=provider, model_name=model_name)

    inputs = []
    for article in articles:
        body = (
            article.get("body")
            or article.get("summary")
            or article.get("raw_text")
            or "-"
        )
        inputs.append(
            {
                "title": article.get("title", "-"),
                "publisher": article.get("publisher", "-"),
                "body": body,
                "language": language,
            }
        )

    try:
        # abatch を使って並行実行
        batch_results = await chain.abatch(inputs, return_exceptions=True)

        results = []
        success_count = 0
        error_count = 0

        for idx, result in enumerate(batch_results):
            article = articles[idx]
            if isinstance(result, Exception):
                logger.warning(f"記事[{idx}]の非同期要約でエラー: {result}")
                error_count += 1
                if "RateLimitError" in str(type(result).__name__) or "429" in str(
                    result
                ):
                    fail_content = (
                        "現在、AI要約サービスの利用が集中しており、一時的に要約を生成できません。"
                        if language == "日本語"
                        else (
                            "AI summary is temporarily unavailable due to "
                            "high traffic."
                        )
                    )
                else:
                    fail_content = (
                        "要約の生成に失敗しました。"
                        if language == "日本語"
                        else "Failed to generate summary."
                    )
                results.append(
                    {
                        "id": idx,
                        "translated_title": article.get("title", "-"),
                        "summarized_content": fail_content,
                        "sentiment": "neutral",
                        "sentiment_reason": f"Error: {type(result).__name__}",
                        "impacted_stocks": [],
                    }
                )
            else:
                # 値が取得できなかった場合は「-」をセットするルールを適用
                cleaned_result = {
                    "id": idx,
                    "translated_title": result.get("translated_title")
                    or article.get("title")
                    or "-",
                    "summarized_content": result.get("summarized_content") or "-",
                    "sentiment": result.get("sentiment") or "neutral",
                    "sentiment_reason": result.get("sentiment_reason") or "-",
                    "impacted_stocks": [],
                }
                for stock in result.get("impacted_stocks", []):
                    cleaned_result["impacted_stocks"].append(
                        {
                            "name": stock.get("name") or "-",
                            "impact_type": stock.get("impact_type") or "neutral",
                            "reason": stock.get("reason") or "-",
                        }
                    )
                results.append(cleaned_result)
                success_count += 1

        logger.info(
            f"ニュースバッチ非同期要約完了: 成功={success_count}件, エラー={error_count}件"
        )
        return results

    except Exception as e:
        logger.error(f"ニュースバッチ非同期要約で全体エラー: {e}")
        results = []
        if "RateLimitError" in str(type(e).__name__) or "429" in str(e):
            fail_content = (
                "現在、AI要約サービスの利用が集中しており、一時的に要約を生成できません。"
                if language == "日本語"
                else (
                    "AI summary is temporarily unavailable due to "
                    "high traffic."
                )
            )
        else:
            fail_content = (
                "要約の生成に失敗しました。"
                if language == "日本語"
                else "Failed to generate summary."
            )
        for idx, article in enumerate(articles):
            results.append(
                {
                    "id": idx,
                    "translated_title": article.get("title", "-"),
                    "summarized_content": fail_content,
                    "sentiment": "neutral",
                    "sentiment_reason": f"Error: {type(e).__name__}",
                    "impacted_stocks": [],
                }
            )
        return results
