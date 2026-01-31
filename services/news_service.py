from typing import List, Dict, Any
import concurrent.futures
from services.data_fetcher import fetch_news
from services.ai_client import analyze_news_impact_batch

def fetch_and_analyze_market_news() -> List[Dict[str, Any]]:
    """
    主要な市場ニュースを取得し、AI分析を行って要約と影響銘柄を返す。
    """
    
    # ニュースソースとして監視するティッカー（指数や為替）
    # 日経、ダウ、ドル円からのニュースを収集
    tickers = ["^N225", "^DJI", "JPY=X"]
    all_news = []
    seen_links = set()

    # 並列でニュース取得（高速化）
    # yfinanceのfetch_newsは同期的なので、ThreadPoolで擬似並列化
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {executor.submit(fetch_news, ticker, limit=5): ticker for ticker in tickers}
        for future in concurrent.futures.as_completed(futures):
            try:
                items = future.result()
                for item in items:
                    # 重複排除
                    if item.get("link") and item["link"] not in seen_links:
                        seen_links.add(item["link"])
                        all_news.append(item)
            except Exception as e:
                print(f"ニュース取得エラー: {e}")

    # 日付順にソート（新しい順）し、上位8件に絞る（AIのコンテキスト制限考慮）
    all_news.sort(key=lambda x: x.get("published_at") or 0, reverse=True)
    all_news = all_news[:8]

    if not all_news:
        return []

    # AI分析
    # リストのインデックス(id)を使ってマージする戦略
    analyzed_data = analyze_news_impact_batch(all_news)


    # 元のニュースデータに分析結果を統合
    # analyze_news_impact_batch は [{"id": 0, "summarized_content": ...}, ...] のようなリストを返す前提
    # ただし、AIがIDを正しく返さない場合もあるため、順番でマッチングするか、IDでマッチング
    
    final_news = []
    
    # マップ作成
    analysis_map = {}
    for ana in analyzed_data:
        # 文字列のIDをINTに変換したり、揺らぎを吸収
        if "id" in ana:
             analysis_map[str(ana["id"])] = ana

    for idx, item in enumerate(all_news):
        analysis = analysis_map.get(str(idx))
        
        # フォールバック: マップで見つからない場合は、順番で取れる可能性も考慮（要検証）
        if not analysis and idx < len(analyzed_data):
             # IDがない場合は順番と仮定
             if "id" not in analyzed_data[idx]: 
                 analysis = analyzed_data[idx]

        if analysis:
            item["translated_title"] = analysis.get("translated_title")
            item["ai_summary"] = analysis.get("summarized_content", "要約の生成に失敗しました")
            item["impacted_stocks"] = analysis.get("impacted_stocks", [])
        else:
             item["translated_title"] = None
             item["ai_summary"] = "要約機能は停止しています" # ユーザー要件によりこの文言
             item["impacted_stocks"] = []

        # 最終リストに追加
        final_news.append(item)

    return final_news
