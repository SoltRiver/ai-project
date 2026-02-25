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

def get_news_tendency(code: str) -> Dict[str, Any]:
    """
    指定された銘柄のニュース傾向（ポジ/ネガ/中立の集計）を算出する。
    AI予測の特徴量および「傾向」表示に使用する。
    """
    symbol = f"{code}.T" if code.isdigit() else code
    news = fetch_news(symbol, limit=20)
    
    # 実際の実装では、ここで各ニュースのタイトル/サマリーを
    # 軽量な感情分析器（あるいは特定のキーワードマッチング）にかける。
    # v1.1では、将来的なAI分析を見据えたI/Fとして、ダミー集計または簡易なキーワードマッチングを行う。
    
    pos_keywords = ["上昇", "増益", "上方修正", "好調", "提携", "自社株買い", "増配"]
    neg_keywords = ["下落", "減益", "下方修正", "不調", "解消", "訴訟", "減配", "赤字"]
    
    counts = {
        "last_7d": {"pos": 0, "neg": 0, "neutral": 0},
        "last_30d": {"pos": 0, "neg": 0, "neutral": 0}
    }
    
    from datetime import datetime, timedelta
    now = datetime.now()
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)
    
    for item in news:
        title = item.get("title", "")
        pub_at = item.get("published_at")
        
        if not pub_at:
            continue
            
        sentiment = "neutral"
        if any(k in title for k in pos_keywords):
            sentiment = "pos"
        elif any(k in title for k in neg_keywords):
            sentiment = "neg"
            
        if pub_at >= seven_days_ago:
            counts["last_7d"][sentiment] += 1
            counts["last_30d"][sentiment] += 1
        elif pub_at >= thirty_days_ago:
            counts["last_30d"][sentiment] += 1
            
    return {
        "counts": counts,
        "total_fetched": len(news),
        "summary_text": f"直近7日: ポジ{counts['last_7d']['pos']} / ネガ{counts['last_7d']['neg']} / 中立{counts['last_7d']['neutral']}"
    }
