"""
LangGraph Stock News Validation Tests
"""

import asyncio

import pytest
from pydantic import ValidationError

from services.langgraph.stock_news_nodes import (build_response_node,
                                                 classify_sentiment_node,
                                                 fetch_news_node)
from services.langgraph.stock_news_schemas import (AISummaryResult, NewsItem,
                                                   StockNewsInput)


def test_stock_news_input_validation():
    # 正常系
    inp = StockNewsInput(stock_code="7203", language="日本語")
    assert inp.stock_code == "7203"
    assert inp.language == "日本語"

    # 空白トリム
    inp_trim = StockNewsInput(stock_code="  7203  ")
    assert inp_trim.stock_code == "7203"

    # 異常系
    with pytest.raises(ValidationError):
        StockNewsInput(stock_code="")


def test_news_item_none_handling():
    # edit-rules: 値が取得できなかった場合は、NoneやNullなどにせずにーや-でセットしてください。
    item = NewsItem(
        title="テストタイトル",
        publisher=None,
        link=None,
        published_at=None,
        summary=None,
    )
    assert item.publisher == "-"
    assert item.link == "#"
    assert item.published_at == "-"
    assert item.summary == "-"


def test_ai_summary_result_validation():
    # 正常系
    res = AISummaryResult(
        translated_title="翻訳テスト",
        summarized_content="要約テスト",
        sentiment="POSITIVE",
        sentiment_reason="理由",
        impacted_stocks=["7203", "9984"],
    )
    assert res.sentiment == "positive"
    assert res.sentiment_reason == "理由"
    assert res.impacted_stocks == ["7203", "9984"]

    # センチメント不正時のフォールバック
    res_bad_sentiment = AISummaryResult(
        summarized_content="テスト",
        sentiment="invalid_sentiment",
        sentiment_reason=None,
    )
    assert res_bad_sentiment.sentiment == "neutral"
    assert res_bad_sentiment.sentiment_reason == "-"


def test_fetch_news_node_success():
    async def run():
        state = {"stock_code": "7203", "language": "日本語"}
        # fetch_news_nodeを実行（実際のAPIは動くか、またはダミーが使われる）
        res = await fetch_news_node(state)
        assert "error" not in res
        assert "news_items" in res
        for item in res["news_items"]:
            # NewsItemスキーマに適合しているか確認
            parsed = NewsItem(**item)
            assert parsed.title is not None
            assert parsed.publisher != "None"

    asyncio.run(run())


def test_fetch_news_node_invalid_input():
    async def run():
        state = {"stock_code": "", "language": "日本語"}
        res = await fetch_news_node(state)
        assert "error" in res
        assert "入力パラメータが不正です" in res["error"]

    asyncio.run(run())


def test_classify_sentiment_node_validation():
    async def run():
        state = {
            "summaries": [
                {
                    "original": {
                        "title": "元記事",
                        "publisher": "テスト",
                        "link": "#",
                        "published_at": "今日",
                        "summary": "概要",
                    },
                    "ai_result": {
                        "translated_title": "翻訳元記事",
                        "summarized_content": "要約",
                        "sentiment": "SUPER_POSITIVE",  # 不正なセンチメント
                        "sentiment_reason": None,
                        "impacted_stocks": None,
                    },
                }
            ]
        }
        res = await classify_sentiment_node(state)
        assert "summaries" in res
        item = res["summaries"][0]
        ai_res = item["ai_result"]
        assert ai_res["sentiment"] == "neutral"  # フォールバックされていること
        assert ai_res["sentiment_reason"] == "-"  # Noneが-になっていること
        assert ai_res["impacted_stocks"] == []  # Noneが空リストになっていること

    asyncio.run(run())


def test_build_response_node_validation():
    async def run():
        state = {
            "stock_code": "7203",
            "summaries": [
                {
                    "original": {
                        "title": "元記事",
                        "publisher": None,  # None
                        "link": "",  # 空
                        "published_at": None,
                        "summary": None,
                    },
                    "ai_result": {
                        "translated_title": "翻訳タイトル",
                        "summarized_content": "要約",
                        "sentiment": "positive",
                        "sentiment_reason": "理由",
                        "impacted_stocks": ["7203"],
                    },
                }
            ],
        }
        res = await build_response_node(state)
        assert "response" in res
        response_data = res["response"]
        assert response_data["stock_code"] == "7203"
        item = response_data["items"][0]
        assert item["title"] == "翻訳タイトル"
        assert item["publisher"] == "-"
        assert item["original_url"] == "#"
        assert item["sentiment_reason"] == "理由"

    asyncio.run(run())
