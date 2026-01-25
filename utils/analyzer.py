"""
テクニカル指標計算モジュール
移動平均線、トレンドラインなどのテクニカル指標を計算する
"""

import numpy as np
import pandas as pd
from typing import Tuple, Optional, Dict, Any


def calculate_sma(prices: pd.Series, period: int) -> pd.Series:
    """
    単純移動平均（SMA）を計算
    
    Args:
        prices: 価格データ（Series）
        period: 期間
    
    Returns:
        移動平均のSeries
    """
    return prices.rolling(window=period).mean()


def calculate_trendline(prices: pd.Series, period: int = 60) -> Tuple[float, float]:
    """
    線形回帰によるトレンドラインを計算
    
    Args:
        prices: 価格データ（Series、直近N本）
        period: 使用する期間（デフォルト: 60）
    
    Returns:
        (傾きa, 切片b) のタプル（y = ax + b）
    """
    if len(prices) < period:
        period = len(prices)
    
    # 直近N本を取得
    recent_prices = prices.tail(period).values
    
    # x軸（インデックス）
    x = np.arange(len(recent_prices))
    
    # 線形回帰で y = ax + b を計算
    coeffs = np.polyfit(x, recent_prices, 1)
    slope = coeffs[0]  # 傾き a
    intercept = coeffs[1]  # 切片 b
    
    return slope, intercept


def calculate_trendline_values(slope: float, intercept: float, 
                               start_idx: int, end_idx: int) -> np.ndarray:
    """
    トレンドラインの値を計算
    
    Args:
        slope: 傾き
        intercept: 切片
        start_idx: 開始インデックス
        end_idx: 終了インデックス
    
    Returns:
        トレンドラインの値の配列
    """
    x = np.arange(start_idx, end_idx)
    return slope * x + intercept


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """
    RSI（相対力指数）を計算
    
    Args:
        prices: 価格データ（Series）
        period: 期間（デフォルト: 14）
    
    Returns:
        RSIのSeries
    """
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def add_technical_indicators(df: pd.DataFrame, 
                            close_col: str = 'close',
                            sma_periods: list = [25, 75]) -> pd.DataFrame:
    """
    データフレームにテクニカル指標を追加
    
    Args:
        df: OHLCデータを含むDataFrame
        close_col: 終値のカラム名
        sma_periods: SMAの期間のリスト（デフォルト: [25, 75]）
    
    Returns:
        テクニカル指標が追加されたDataFrame
    """
    result_df = df.copy()
    
    # 移動平均線を追加
    for period in sma_periods:
        result_df[f'SMA{period}'] = calculate_sma(result_df[close_col], period)
    
    # RSIを追加（オプション）
    result_df['RSI'] = calculate_rsi(result_df[close_col])
    
    return result_df


def get_trendline_data(df: pd.DataFrame, 
                      close_col: str = 'close',
                      period: int = 60) -> Tuple[np.ndarray, np.ndarray]:
    """
    トレンドラインのデータを取得
    
    Args:
        df: OHLCデータを含むDataFrame
        close_col: 終値のカラム名
        period: 使用する期間（デフォルト: 60）
    
    Returns:
        (x軸の値, y軸の値) のタプル
    """
    prices = df[close_col]
    slope, intercept = calculate_trendline(prices, period)
    
    # チャート全体の範囲でトレンドラインを計算
    start_idx = max(0, len(prices) - period)
    end_idx = len(prices)
    
    x_values = np.arange(start_idx, end_idx)
    y_values = calculate_trendline_values(slope, intercept, start_idx, end_idx)
    
    return x_values, y_values


def detect_golden_cross(sma_short: pd.Series, sma_long: pd.Series) -> bool:
    """
    ゴールデンクロス（買いシグナル）を検出
    
    Args:
        sma_short: 短期移動平均線
        sma_long: 長期移動平均線
    
    Returns:
        ゴールデンクロスが発生している場合True
    """
    if len(sma_short) < 2 or len(sma_long) < 2:
        return False
    
    # 前回は短期 < 長期、今回は短期 > 長期
    prev_short = sma_short.iloc[-2]
    prev_long = sma_long.iloc[-2]
    curr_short = sma_short.iloc[-1]
    curr_long = sma_long.iloc[-1]
    
    return prev_short <= prev_long and curr_short > curr_long


def detect_dead_cross(sma_short: pd.Series, sma_long: pd.Series) -> bool:
    """
    デッドクロス（売りシグナル）を検出
    
    Args:
        sma_short: 短期移動平均線
        sma_long: 長期移動平均線
    
    Returns:
        デッドクロスが発生している場合True
    """
    if len(sma_short) < 2 or len(sma_long) < 2:
        return False
    
    # 前回は短期 > 長期、今回は短期 < 長期
    prev_short = sma_short.iloc[-2]
    prev_long = sma_long.iloc[-2]
    curr_short = sma_short.iloc[-1]
    curr_long = sma_long.iloc[-1]
    
    return prev_short >= prev_long and curr_short < curr_long


def analyze_candlestick(open_price: float, high: float, low: float, close: float) -> Dict[str, str]:
    """
    ローソク足の形状を分析して名称と種類を返す
    
    Args:
        open_price: 始値
        high: 高値
        low: 安値
        close: 終値
    
    Returns:
        {'name': str, 'type': str}
    """
    if open_price is None or close is None or high is None or low is None:
        return {'name': '-', 'type': '-'}
    
    # NaN check
    import math
    if math.isnan(open_price) or math.isnan(close) or math.isnan(high) or math.isnan(low):
         return {'name': '-', 'type': '-'}
    
    is_up = close >= open_price
    candle_type = "陽線" if is_up else "陰線"
    
    body = abs(close - open_price)
    range_len = high - low
    
    if range_len == 0:
        return {'name': '一本値', 'type': candle_type}
    
    body_ratio = body / range_len
    upper_shadow = (high - close) if is_up else (high - open_price)
    lower_shadow = (open_price - low) if is_up else (close - low)
    
    name = "小" + candle_type # Default
    
    # 判定ロジック
    if body_ratio < 0.1:
        name = "十字線"
    elif body_ratio > 0.8:
        name = "大" + candle_type
    elif lower_shadow > body * 2 and upper_shadow < body:
        name = "下ヒゲ" + ("陽線" if is_up else "陰線") # カラカサなど
    elif upper_shadow > body * 2 and lower_shadow < body:
        name = "上ヒゲ" + ("陽線" if is_up else "陰線") # トンカチなど
    
    return {'name': name, 'type': candle_type}


def get_rsi_status(rsi: Optional[float]) -> Dict[str, Any]:
    """
    RSIの状態を判定して返す

    Args:
        rsi: RSI値

    Returns:
        状態ラベルと表示色を含む辞書
    """
    if rsi is None or pd.isna(rsi):
        return {"label": "RSIデータなし", "color": "gray", "state": "neutral"}
    if rsi >= 70:
        return {"label": "買われすぎ", "color": "red", "state": "hot"}
    if rsi <= 30:
        return {"label": "売られすぎ", "color": "green", "state": "cold"}
    return {"label": "中立", "color": "gray", "state": "neutral"}


def evaluate_volatility(df: pd.DataFrame, window: int = 30) -> Dict[str, Any]:
    """
    価格変動の大きさを評価する

    Args:
        df: OHLCデータ
        window: 計算に使う期間（日数）

    Returns:
        ボラティリティ値とレベル
    """
    returns = df["close"].pct_change().dropna().tail(window)
    if returns.empty:
        return {"volatility": None, "level": "不明", "warning": False}

    volatility = float(returns.std() * 100)
    if volatility >= 3.0:
        level = "高"
        warning = True
    elif volatility >= 1.5:
        level = "中"
        warning = False
    else:
        level = "低"
        warning = False

    return {"volatility": volatility, "level": level, "warning": warning}


def evaluate_liquidity(volume: Optional[float],
                       average_volume: Optional[float] = None,
                       threshold_low: int = 50000) -> Dict[str, Any]:
    """
    出来高をもとに流動性を評価する

    Args:
        volume: 直近出来高
        average_volume: 平均出来高（ある場合）
        threshold_low: 低流動性とみなす基準

    Returns:
        レベルと警告フラグ
    """
    basis = average_volume or volume
    if basis is None:
        return {"level": "不明", "warning": False}

    if basis < threshold_low:
        return {"level": "流動性低", "warning": True}
    return {"level": "通常", "warning": False}


def calculate_star_rating(value: Optional[float],
                          thresholds: list[float],
                          reverse: bool = False,
                          max_stars: int = 5) -> int:
    """
    値と閾値から簡易スター評価を計算する

    Args:
        value: 評価対象の値
        thresholds: 境界値を昇順で与える
        reverse: 値が低いほど良い場合はTrue
        max_stars: 最大スター数

    Returns:
        スター数（1〜max_stars）
    """
    if value is None or pd.isna(value):
        return max_stars // 2

    steps = len(thresholds)
    score = 0
    for i, border in enumerate(thresholds, start=1):
        if reverse:
            if value <= border:
                score = i
                break
        else:
            if value >= border:
                score = i
    # 正規化してスター数に変換
    normalized = score / steps if steps else 0.5
    stars = max(1, min(max_stars, round(normalized * max_stars)))
    return stars


def format_stars(stars: int, max_stars: int = 5) -> str:
    """スター評価を文字列に整形する"""
    stars = max(0, min(max_stars, stars))
    return "★" * stars + "☆" * (max_stars - stars)


def get_direction_label(prices: pd.Series,
                        positive_label: str = "右肩上がり",
                        negative_label: str = "下降傾向",
                        neutral_label: str = "横ばい") -> str:
    """
    トレンド方向の簡易ラベルを返す

    Args:
        prices: 価格Series
        positive_label: 上昇時のラベル
        negative_label: 下落時のラベル
        neutral_label: 中立のラベル
    """
    if prices is None or len(prices) < 5:
        return neutral_label

    slope, _ = calculate_trendline(prices, period=min(len(prices), 60))
    threshold = max(prices) - min(prices)
    threshold = (threshold * 0.005) if threshold else 0.01

    if slope > threshold:
        return positive_label
    if slope < -threshold:
        return negative_label
    return neutral_label

