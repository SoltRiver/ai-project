"""
非同期ニュース要約チェーンおよびLangGraphワークフローの動作確認スクリプト（モック検証対応版）
"""

import sys
import os
import io
import asyncio
import time
from unittest.mock import MagicMock, patch

# Windows環境のコンソール出力エンコーディング修正
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from ai.chains.news_summarizer import (
    summarize_news_article_async,
    summarize_news_batch_async,
)
from services.langgraph.stock_news_graph import run_stock_news_workflow

# ====================================================================
# APIクォータ制限を回避するための非同期LLMモック定義
# ====================================================================


async def mock_ainvoke(inputs, *args, **kwargs):
    language = inputs.get("language", "日本語")
    title = inputs.get("title", "-")
    # ロケール言語に応じた出力をシミュレート
    if "English" in language or "en" in language.lower():
        return {
            "translated_title": f"Translated: {title}",
            "summarized_content": "This is a mocked summary in English.",
            "sentiment": "positive",
            "sentiment_reason": "Mocked reason for positive sentiment.",
            "impacted_stocks": [
                {
                    "name": "Mock Stock",
                    "impact_type": "positive",
                    "reason": "Decent Q3 result.",
                }
            ],
        }
    else:
        return {
            "translated_title": f"翻訳: {title}",
            "summarized_content": "これはモック化された日本語の要約です。",
            "sentiment": "positive",
            "sentiment_reason": "ポジティブなセンチメントのモック理由。",
            "impacted_stocks": [
                {
                    "name": "モック銘柄",
                    "impact_type": "positive",
                    "reason": "決算好調のため",
                }
            ],
        }


async def mock_abatch(inputs_list, *args, **kwargs):
    results = []
    # return_exceptions=Trueを考慮
    return_exceptions = kwargs.get("return_exceptions", False)
    for inputs in inputs_list:
        try:
            res = await mock_ainvoke(inputs)
            results.append(res)
        except Exception as e:
            if return_exceptions:
                results.append(e)
            else:
                raise e
    return results


def mock_invoke(inputs, *args, **kwargs):
    # 同期呼び出し用のヘルパー
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # すでにループが走っている場合はタスクとしてスケジュールするか、別スレッドで走らせる
        # テスト簡略化のため、非同期の同期実行
        import nest_asyncio

        nest_asyncio.apply()
        return loop.run_until_complete(mock_ainvoke(inputs))
    else:
        return asyncio.run(mock_ainvoke(inputs))


async def test_single_article_async():
    """非同期単一記事の要約テスト（言語切替含む）"""
    print("=" * 60)
    print("【非同期テスト1】単一記事の要約 (日本語 & 英語)")
    print("=" * 60)

    title = "Toyota Motor Reports Record Q3 Earnings, Raises Full-Year Guidance"
    body = (
        "Toyota Motor Corporation announced third-quarter earnings that exceeded "
        "analyst expectations. Revenue rose 12% year-over-year to ¥10.5 trillion, "
        "driven by strong hybrid vehicle sales in North America and Europe. "
        "The company raised its full-year operating profit forecast by 8% to ¥5.2 trillion."
    )

    # 1. 日本語要約のテスト
    print("\n--- 1. 日本語要約 ---")
    t0 = time.time()
    result_ja = await summarize_news_article_async(
        title=title,
        body=body,
        publisher="Reuters",
        provider="openai",
        language="日本語",
    )
    print(f"所要時間: {time.time() - t0:.4f}秒")
    print(f"翻訳タイトル: {result_ja.get('translated_title', '-')}")
    print(f"要約: {result_ja.get('summarized_content', '-')}")
    print(f"センチメント: {result_ja.get('sentiment', '-')}")
    print(f"判定理由: {result_ja.get('sentiment_reason', '-')}")

    # 2. 英語要約のテスト
    print("\n--- 2. 英語要約 (English Summary) ---")
    t0 = time.time()
    result_en = await summarize_news_article_async(
        title=title,
        body=body,
        publisher="Reuters",
        provider="openai",
        language="English",
    )
    print(f"所要時間: {time.time() - t0:.4f}秒")
    print(f"Translated Title (EN): {result_en.get('translated_title', '-')}")
    print(f"Summary (EN): {result_en.get('summarized_content', '-')}")
    print(f"Sentiment (EN): {result_en.get('sentiment', '-')}")
    print(f"Reason (EN): {result_en.get('sentiment_reason', '-')}")


async def test_batch_async():
    """非同期バッチ並行要約テスト"""
    print("\n" + "=" * 60)
    print("【非同期テスト2】バッチ要約（3件並行）")
    print("=" * 60)

    articles = [
        {
            "title": "Sony Group to invest 100 billion yen in AI semiconductors",
            "body": "Sony Group announced a major investment of 100 billion yen in research and development of AI-related semiconductors to boost its sensor business.",
            "publisher": "Nikkei",
        },
        {
            "title": "Federal Reserve signals potential rate cut in upcoming meeting",
            "body": "The Federal Reserve indicated it may consider lowering interest rates if economic data continues to show inflation slowing toward the 2% target.",
            "publisher": "WSJ",
        },
        {
            "title": "SoftBank Group returns to profitability on tech valuations rebound",
            "body": "SoftBank Group reported positive net income for the quarter, driven by a sharp rebound in the valuation of its Vision Fund tech portfolio holdings.",
            "publisher": "FT",
        },
    ]

    t0 = time.time()
    results = await summarize_news_batch_async(
        articles, provider="openai", language="日本語"
    )
    duration = time.time() - t0
    print(f"並行処理完了所要時間: {duration:.4f}秒 (3件直列だと通常5〜6秒程度)")

    for r in results:
        print(f"\n--- 記事 ID:{r.get('id', '-')} ---")
        print(f"翻訳タイトル: {r.get('translated_title', '-')}")
        print(f"要約: {r.get('summarized_content', '-')}")
        print(
            f"センチメント: {r.get('sentiment', '-')} / 理由: {r.get('sentiment_reason', '-')}"
        )
        for stock in r.get("impacted_stocks", []):
            print(f"  影響: {stock.get('name', '-')} ({stock.get('impact_type', '-')})")


async def test_workflow_async():
    """LangGraph非同期ワークフローのテスト"""
    print("\n" + "=" * 60)
    print("【非同期テスト3】LangGraphワークフロー (トヨタ 7203.T)")
    print("=" * 60)

    t0 = time.time()
    # 日本語
    state_ja = await run_stock_news_workflow("7203", language="日本語")
    print(f"日本語ワークフロー所要時間: {time.time() - t0:.4f}秒")
    if "error" in state_ja:
        print(f"Error: {state_ja['error']}")
    else:
        resp = state_ja.get("response", {})
        print(f"取得記事数: {len(resp.get('items', []))}")
        for item in resp.get("items", [])[:2]:
            print(f"  - タイトル: {item.get('title')}")
            print(f"    要約: {item.get('summary')}")
            print(f"    センチメント: {item.get('sentiment')}")

    t0 = time.time()
    # 英語
    state_en = await run_stock_news_workflow("7203", language="English")
    print(f"\n英語ワークフロー所要時間: {time.time() - t0:.4f}秒")
    if "error" in state_en:
        print(f"Error: {state_en['error']}")
    else:
        resp = state_en.get("response", {})
        print(f"取得記事数: {len(resp.get('items', []))}")
        for item in resp.get("items", [])[:2]:
            print(f"  - Title: {item.get('title')}")
            print(f"    Summary: {item.get('summary')}")
            print(f"    Sentiment: {item.get('sentiment')}")


async def main():
    # nest_asyncioの適用 (非同期ループの重複実行エラー対策)
    try:
        import nest_asyncio

        nest_asyncio.apply()
    except ImportError:
        pass

    # _build_news_summary_chain の戻り値であるチェーンの ainvoke / abatch / invoke をパッチする
    mock_chain = MagicMock()
    mock_chain.ainvoke = mock_ainvoke
    mock_chain.abatch = mock_abatch
    mock_chain.invoke = mock_invoke

    # パッチの適用してテスト実行
    with patch(
        "ai.chains.news_summarizer._build_news_summary_chain", return_value=mock_chain
    ):
        await test_single_article_async()
        await test_batch_async()
        await test_workflow_async()


if __name__ == "__main__":
    asyncio.run(main())
