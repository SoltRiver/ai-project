import yfinance as yf
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional

def get_major_indices() -> List[Dict[str, Any]]:
    """
    主要指標のデータを取得します。

    Returns:
        List[Dict[str, Any]]: 指標データのリスト。各辞書は以下のキーを持ちます:
            - name: 指標名
            - ticker: ティッカーシンボル
            - price: 現在値 (取得失敗時は None)
            - change: 前日比 (取得失敗時は None)
            - change_percent: 前日比率 (取得失敗時は None)
            - status: 取得ステータス ("OK" または "取得失敗")
    
    Note:
        一部の指標(TOPIX, JASDAQ, マザーズなど)はYahoo Financeで正確なティッカーが存在しないため、
        プレースホルダーまたは代替ティッカーを使用しています。
    """
    
    indices_map = [
        {"name": "日経平均", "ticker": "^N225"},
        {"name": "TOPIX", "ticker": "^TOPX"}, 
        {"name": "日経平均先物", "ticker": "NIY=F"}, 
        {"name": "JASDAQ平均", "ticker": "^DJJAS"}, 
        {"name": "NYダウ", "ticker": "^DJI"},
        {"name": "NASDAQ", "ticker": "^IXIC"},
        {"name": "マザーズ総合", "ticker": "^MOTHERS"},
    ]

    results = []
    
    # 信頼性を高めるために一括取得ではなく個別取得を行います。
    # APIエラーで一部が失敗しても他を取得できるようにするためです。
    
    for item in indices_map:
        name = item["name"]
        ticker_symbol = item["ticker"]
        
        data = {
            "name": name,
            "ticker": ticker_symbol,
            "price": None,
            "change": None,
            "change_percent": None,
            "status": "取得失敗"
        }

        try:
            ticker = yf.Ticker(ticker_symbol)
            # 変化率を計算するために過去5日分を取得します（祝日などを考慮）
            hist = ticker.history(period="5d")
            
            if not hist.empty:
                # 最新のデータを使用
                last_row = hist.iloc[-1]
                price = float(last_row["Close"])
                
                data["price"] = price
                data["status"] = "OK"
                
                # 前日比の計算
                if len(hist) >= 2:
                    prev_close = float(hist.iloc[-2]["Close"])
                    if prev_close and prev_close != 0:
                        change = price - prev_close
                        pct = (change / prev_close) * 100
                        data["change"] = change
                        data["change_percent"] = pct
                        
        except Exception as e:
            # エラーログが必要な場合はここで出力
            # print(f"{name} の取得エラー: {e}")
            pass
            
        results.append(data)

    return results

