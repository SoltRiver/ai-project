"""
ニュース要約チェーンの動作確認スクリプト
LangChainチェーンが正しく構築・実行されることを検証する。
"""

import sys
import os
import io

# Windows環境のコンソール出力エンコーディング修正
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from ai.chains.news_summarizer import summarize_news_article, summarize_news_batch


def test_single_article():
    """単一記事の要約テスト"""
    print("=" * 60)
    print("【テスト1】単一記事の要約")
    print("=" * 60)

    result = summarize_news_article(
        title="Toyota Motor Reports Record Q3 Earnings, Raises Full-Year Guidance",
        body=(
            "Toyota Motor Corporation announced third-quarter earnings that exceeded "
            "analyst expectations. Revenue rose 12% year-over-year to ¥10.5 trillion, "
            "driven by strong hybrid vehicle sales in North America and Europe. "
            "The company raised its full-year operating profit forecast by 8% to ¥5.2 trillion. "
            "CEO Koji Sato attributed the results to the successful launch of new hybrid models "
            "and improved supply chain efficiency."
        ),
        publisher="Reuters",
        provider="openai",
    )

    print(f"\n翻訳タイトル: {result.get('translated_title', '-')}")
    print(f"要約: {result.get('summarized_content', '-')}")
    print(f"センチメント: {result.get('sentiment', '-')}")
    print(f"理由: {result.get('sentiment_reason', '-')}")
    print(f"影響銘柄:")
    for stock in result.get("impacted_stocks", []):
        print(
            f"  - {stock.get('name', '-')} ({stock.get('impact_type', '-')}): {stock.get('reason', '-')}"
        )

    return result


def test_batch():
    """バッチ要約テスト"""
    print("\n" + "=" * 60)
    print("【テスト2】バッチ要約（2件）")
    print("=" * 60)

    articles = [
        {
            "title": "Bank of Japan holds interest rates steady amid global uncertainty",
            "body": "The Bank of Japan maintained its key interest rate at 0.5% "
            "as policymakers weigh persistent inflation against global economic headwinds.",
            "publisher": "Bloomberg",
        },
        {
            "title": "ソニーグループ、AI半導体への投資を加速 今期1000億円規模",
            "body": "ソニーグループは2026年度にAI半導体関連の研究開発投資を1000億円規模に拡大する計画を発表した。"
            "イメージセンサー事業で培った技術をAI推論チップに応用し、新たな収益柱とする。",
            "publisher": "日本経済新聞",
        },
    ]

    results = summarize_news_batch(articles, provider="openai")

    for r in results:
        print(f"\n--- 記事 ID:{r.get('id', '-')} ---")
        print(f"翻訳タイトル: {r.get('translated_title', '-')}")
        print(f"要約: {r.get('summarized_content', '-')}")
        print(
            f"センチメント: {r.get('sentiment', '-')} / 理由: {r.get('sentiment_reason', '-')}"
        )
        for stock in r.get("impacted_stocks", []):
            print(f"  影響: {stock.get('name', '-')} ({stock.get('impact_type', '-')})")

    return results


if __name__ == "__main__":
    try:
        r1 = test_single_article()
        r2 = test_batch()
        print("\n" + "=" * 60)
        print("[OK] すべてのテスト完了")
        print("=" * 60)
    except Exception as e:
        print(f"\n[ERROR] テストエラー: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
