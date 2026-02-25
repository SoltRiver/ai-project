"""
市場データ取得サービス
TOPIXや日経平均などの指数データを取得し、AI予測の特徴量として提供する。
"""

import logging
from typing import Optional, Dict, Any
import pandas as pd
from services.data_fetcher import fetch_stock_data

logger = logging.getLogger(__name__)

def fetch_market_indicators() -> Dict[str, Optional[pd.DataFrame]]:
    """
    主要な市場指数（TOPIX, 日経225）のデータを取得する。
    """
    indices = {
        "TOPIX": "^TPX",
        "N225": "^N225"
    }
    
    results = {}
    for name, symbol in indices.items():
        try:
            # AI特徴量用に長めの期間を取得
            df = fetch_stock_data(symbol, period="2y", interval="1d")
            results[name] = df
        except Exception as e:
            logger.error(f"市場指数データ取得エラー ({name}): {e}")
            results[name] = None
            
    return results

def get_market_features(market_dfs: Dict[str, Optional[pd.DataFrame]], target_date: Any) -> Dict[str, float]:
    """
    特定の時点における市場動向特徴量を算出する。
    """
    features = {}
    
    for name, df in market_dfs.items():
        if df is None or df.empty:
            features[f"{name}_ret_1d"] = 0.0
            features[f"{name}_ret_5d"] = 0.0
            features[f"{name}_vol_20d"] = 0.0
            continue
            
        # target_date以前のデータを抽出
        mask = df['date'] <= target_date
        past_df = df[mask].tail(21) # 20日分のボラ計算に21行必要
        
        if len(past_df) < 2:
            features[f"{name}_ret_1d"] = 0.0
            features[f"{name}_ret_5d"] = 0.0
            features[f"{name}_vol_20d"] = 0.0
            continue
            
        # 1日リターン
        last_close = past_df['close'].iloc[-1]
        prev_close = past_df['close'].iloc[-2]
        features[f"{name}_ret_1d"] = (last_close - prev_close) / prev_close
        
        # 5日リターン
        if len(past_df) >= 6:
            prev_5d_close = past_df['close'].iloc[-6]
            features[f"{name}_ret_5d"] = (last_close - prev_5d_close) / prev_5d_close
        else:
            features[f"{name}_ret_5d"] = 0.0
            
        # 20日ボラティリティ
        if len(past_df) >= 21:
            rets = past_df['close'].pct_change().dropna()
            features[f"{name}_vol_20d"] = float(rets.std())
        else:
            features[f"{name}_vol_20d"] = 0.0
            
    return features
