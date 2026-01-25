"""
ローソク足の種類判定モジュール
OHLCデータからローソク足の種類を判定する
"""

from typing import Dict, Optional


def classify_candle(open_price: float, high_price: float, 
                   low_price: float, close_price: float) -> str:
    """
    OHLCデータからローソク足の種類を判定
    
    Args:
        open_price: 始値
        high_price: 高値
        low_price: 安値
        close_price: 終値
    
    Returns:
        ローソク足の種類（"十字線", "カラカサ", "トンカチ", "マルボウズ", "大陽線", "大陰線", "陽線", "陰線"）
    """
    # 実体の計算
    body = abs(close_price - open_price)
    
    # 上ヒゲと下ヒゲの計算
    upper_shadow = high_price - max(open_price, close_price)
    lower_shadow = min(open_price, close_price) - low_price
    
    # 全体の値幅
    total_range = high_price - low_price
    
    # ゼロ除算を避ける
    if total_range == 0:
        return "十字線"
    
    # 実体の割合
    body_ratio = body / total_range
    
    # ヒゲの長さ
    upper_shadow_ratio = upper_shadow / total_range if total_range > 0 else 0
    lower_shadow_ratio = lower_shadow / total_range if total_range > 0 else 0
    
    # 陽線か陰線か
    is_bullish = close_price > open_price
    
    # 1. 十字線の判定（実体が極めて小さい）
    if body_ratio < 0.1:
        return "十字線"
    
    # 2. カラカサの判定（下ヒゲが長く、実体が小さい）
    if lower_shadow_ratio > 0.6 and body_ratio < 0.3:
        return "カラカサ"
    
    # 3. トンカチの判定（上ヒゲが長く、実体が小さい）
    if upper_shadow_ratio > 0.6 and body_ratio < 0.3:
        return "トンカチ"
    
    # 4. マルボウズの判定（ヒゲがほとんどない）
    if upper_shadow_ratio < 0.05 and lower_shadow_ratio < 0.05:
        return "マルボウズ"
    
    # 5. 大陽線の判定（実体が大きく、陽線）
    if is_bullish and body_ratio > 0.7:
        return "大陽線"
    
    # 6. 大陰線の判定（実体が大きく、陰線）
    if not is_bullish and body_ratio > 0.7:
        return "大陰線"
    
    # 7. 通常の陽線・陰線
    if is_bullish:
        return "陽線"
    else:
        return "陰線"


def get_candle_info(open_price: float, high_price: float,
                   low_price: float, close_price: float) -> Dict[str, any]:
    """
    ローソク足の詳細情報を取得
    
    Args:
        open_price: 始値
        high_price: 高値
        low_price: 安値
        close_price: 終値
    
    Returns:
        ローソク足の詳細情報を含む辞書
    """
    candle_type = classify_candle(open_price, high_price, low_price, close_price)
    
    body = abs(close_price - open_price)
    upper_shadow = high_price - max(open_price, close_price)
    lower_shadow = min(open_price, close_price) - low_price
    total_range = high_price - low_price
    
    return {
        "type": candle_type,
        "open": open_price,
        "high": high_price,
        "low": low_price,
        "close": close_price,
        "body": body,
        "upper_shadow": upper_shadow,
        "lower_shadow": lower_shadow,
        "total_range": total_range,
        "is_bullish": close_price > open_price
    }

