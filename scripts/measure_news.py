import sys
import time
import concurrent.futures
import json

sys.path.insert(0, r"c:\Users\curem\ai-project")

from services.data_fetcher import fetch_news
from services.ai_client import get_ai_client


def main():
    start_time = time.time()

    # 1. ニュースフェッチ
    tickers = ["^N225", "^DJI", "JPY=X"]
    all_news = []
    seen_links = set()

    fetch_start = time.time()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(fetch_news, ticker, limit=5): ticker for ticker in tickers
        }
        for future in concurrent.futures.as_completed(futures):
            try:
                items = future.result()
                for item in items:
                    if item.get("link") and item["link"] not in seen_links:
                        seen_links.add(item["link"])
                        all_news.append(item)
            except Exception as e:
                print(f"Error: {e}")
    fetch_end = time.time()
    print(f"1. 外部ニュース取得時間: {fetch_end - fetch_start:.2f}秒")

    # ソートと絞り込み
    all_news.sort(key=lambda x: x.get("published_at") or 0, reverse=True)
    all_news = all_news[:8]

    # 2. プロンプト構築
    articles_text = ""
    for idx, item in enumerate(all_news):
        articles_text += f"[ID:{idx}] {item.get('title')} (Source: {item.get('publisher')})\n{item.get('summary', '')}\n\n"

    prompt = f"""
以下の金融ニュース記事を分析し、JSON形式のリストで回答してください。
各記事について以下の情報が必要です（必ず日本語で回答してください）：
1. translated_title: ニュース記事タイトルの自然な日本語訳。
2. summarized_content: 初心者向けの3行程度の要約（日本語）。元記事が英語であっても必ず日本語で要約してください。
3. impacted_stocks: このニュースが影響を与える可能性のある銘柄リスト。
   各銘柄には以下の情報を含めてください（銘柄名も日本語にすること）：
   - name: 銘柄名または業種名（例: トヨタ自動車、半導体セクター）
   - impact_type: "positive" または "negative"
   - reason: なぜプラス/マイナスなのかの短い理由（日本語）

記事リスト:
{articles_text}

出力フォーマット（JSONのみ、キー名は厳密に守ること）:
[
  {{
    "id": 0,
    "translated_title": "日本語訳タイトル...",
    "summarized_content": "要約テキスト...",
    "impacted_stocks": [
      {{"name": "銘柄A", "impact_type": "positive", "reason": "理由..."}},
      {{"name": "銘柄B", "impact_type": "negative", "reason": "理由..."}}
    ]
  }}
]
"""

    try:
        import tiktoken

        enc = tiktoken.encoding_for_model("gpt-4o-mini")
        tokens = enc.encode(prompt)
        print(f"2. プロンプト（入力）実測トークン数(tiktoken): {len(tokens)}")
    except ImportError:
        print(f"2. プロンプト（入力）概算トークン数(文字数ベース): {len(prompt) // 2}")

    print(
        "3. AI分析の実行はAPI制限のためスキップします。通常AIの処理に10〜20秒程度かかると予想されます。"
    )
    print(
        f"4. トークン消費詳細: 入力={len(tokens) if 'tokens' in locals() else 'Unknown'} (予想), 出力=約1500 (予想), 計=約{len(tokens) + 1500 if 'tokens' in locals() else 'Unknown'}"
    )

    total_end = time.time()
    print(
        f"★ ニュース取得処理時間: {total_end - start_time:.2f}秒 (※これにAI処理時間が加算されます)"
    )


if __name__ == "__main__":
    from dotenv import load_dotenv
    import os

    load_dotenv(os.path.join(r"c:\Users\curem\ai-project", ".env"))
    main()
