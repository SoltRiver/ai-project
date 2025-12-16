"""
チャートパターン視覚化モジュール
各チャートパターンの視覚的な図を生成する
"""

import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def generate_pattern_chart(pattern_name: str) -> go.Figure:
    """
    チャートパターンの視覚的な図を生成
    
    Args:
        pattern_name: パターン名
    
    Returns:
        PlotlyのFigureオブジェクト
    """
    if pattern_name == "トリプルボトム":
        return create_triple_bottom_chart()
    elif pattern_name == "トリプルトップ":
        return create_triple_top_chart()
    elif pattern_name == "ダブルトップ":
        return create_double_top_chart()
    elif pattern_name == "ダブルボトム":
        return create_double_bottom_chart()
    elif pattern_name == "逆三尊":
        return create_inverse_head_shoulders_chart()
    elif pattern_name == "三尊天井":
        return create_head_shoulders_chart()
    elif pattern_name == "上昇レンジ":
        return create_ascending_range_chart()
    elif pattern_name == "下降レンジ":
        return create_descending_range_chart()
    elif pattern_name == "上昇三角持ち合い":
        return create_ascending_triangle_chart()
    elif pattern_name == "下降三角持ち合い":
        return create_descending_triangle_chart()
    elif pattern_name == "上昇フラッグ":
        return create_bullish_flag_chart()
    elif pattern_name == "下降フラッグ":
        return create_bearish_flag_chart()
    elif pattern_name == "上昇ペナント":
        return create_bullish_pennant_chart()
    elif pattern_name == "下降ペナント":
        return create_bearish_pennant_chart()
    elif pattern_name == "上昇ウェッジ":
        return create_rising_wedge_chart()
    elif pattern_name == "下降ウェッジ":
        return create_falling_wedge_chart()
    elif pattern_name == "ソーサートップ":
        return create_saucer_top_chart()
    elif pattern_name == "ソーサーボトム":
        return create_saucer_bottom_chart()
    else:
        return create_default_chart()


def create_triple_bottom_chart() -> go.Figure:
    """トリプルボトムのチャートを生成"""
    dates = pd.date_range(start='2024-01-01', periods=50, freq='D')
    
    # トリプルボトムの形状を生成
    base_price = 100
    prices = []
    
    # 下降トレンド
    for i in range(10):
        prices.append(base_price - i * 2)
    
    # 1つ目のボトム
    prices.append(base_price - 20)
    prices.append(base_price - 18)
    prices.append(base_price - 20)
    
    # 1つ目の高値
    for i in range(5):
        prices.append(base_price - 20 + i * 3)
    
    # 2つ目のボトム
    prices.append(base_price - 20)
    prices.append(base_price - 18)
    prices.append(base_price - 20)
    
    # 2つ目の高値
    for i in range(5):
        prices.append(base_price - 20 + i * 3)
    
    # 3つ目のボトム
    prices.append(base_price - 20)
    prices.append(base_price - 18)
    prices.append(base_price - 20)
    
    # ブレイクアウト
    for i in range(10):
        prices.append(base_price - 20 + i * 2)
    
    # OHLCデータを生成
    df = create_ohlc_from_prices(dates[:len(prices)], prices)
    
    fig = go.Figure(data=[go.Candlestick(
        x=df['date'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        increasing_line_color='green',
        increasing_fillcolor='green',
        decreasing_line_color='red',
        decreasing_fillcolor='red'
    )])
    
    # ネックライン（抵抗線）を追加
    neckline = base_price - 5
    fig.add_hline(y=neckline, line_dash="dash", line_color="red", 
                  annotation_text="抵抗線（ネックライン）", annotation_position="right")
    
    # 支持線を追加
    support_line = base_price - 20
    fig.add_hline(y=support_line, line_dash="dash", line_color="blue",
                  annotation_text="支持線", annotation_position="right")
    
    fig.update_layout(
        title="トリプルボトムパターン",
        xaxis_rangeslider_visible=False,
        height=400,
        showlegend=False
    )
    
    return fig


def create_triple_top_chart() -> go.Figure:
    """トリプルトップのチャートを生成"""
    dates = pd.date_range(start='2024-01-01', periods=50, freq='D')
    
    base_price = 100
    prices = []
    
    # 上昇トレンド
    for i in range(10):
        prices.append(base_price + i * 2)
    
    # 1つ目のトップ
    prices.append(base_price + 20)
    prices.append(base_price + 18)
    prices.append(base_price + 20)
    
    # 1つ目の安値
    for i in range(5):
        prices.append(base_price + 20 - i * 3)
    
    # 2つ目のトップ
    prices.append(base_price + 20)
    prices.append(base_price + 18)
    prices.append(base_price + 20)
    
    # 2つ目の安値
    for i in range(5):
        prices.append(base_price + 20 - i * 3)
    
    # 3つ目のトップ
    prices.append(base_price + 20)
    prices.append(base_price + 18)
    prices.append(base_price + 20)
    
    # ブレイクダウン
    for i in range(10):
        prices.append(base_price + 20 - i * 2)
    
    df = create_ohlc_from_prices(dates[:len(prices)], prices)
    
    fig = go.Figure(data=[go.Candlestick(
        x=df['date'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        increasing_line_color='green',
        increasing_fillcolor='green',
        decreasing_line_color='red',
        decreasing_fillcolor='red'
    )])
    
    # ネックライン（支持線）を追加
    neckline = base_price + 5
    fig.add_hline(y=neckline, line_dash="dash", line_color="blue",
                  annotation_text="支持線（ネックライン）", annotation_position="right")
    
    # 抵抗線を追加
    resistance_line = base_price + 20
    fig.add_hline(y=resistance_line, line_dash="dash", line_color="red",
                  annotation_text="抵抗線", annotation_position="right")
    
    fig.update_layout(
        title="トリプルトップパターン",
        xaxis_rangeslider_visible=False,
        height=400,
        showlegend=False
    )
    
    return fig


def create_double_top_chart() -> go.Figure:
    """ダブルトップのチャートを生成"""
    dates = pd.date_range(start='2024-01-01', periods=40, freq='D')
    
    base_price = 100
    prices = []
    
    # 上昇トレンド
    for i in range(8):
        prices.append(base_price + i * 2.5)
    
    # 1つ目のトップ
    prices.append(base_price + 20)
    prices.append(base_price + 18)
    prices.append(base_price + 20)
    
    # 中間の安値
    for i in range(6):
        prices.append(base_price + 20 - i * 2)
    
    # 2つ目のトップ
    prices.append(base_price + 20)
    prices.append(base_price + 18)
    prices.append(base_price + 20)
    
    # ブレイクダウン
    for i in range(10):
        prices.append(base_price + 20 - i * 1.5)
    
    df = create_ohlc_from_prices(dates[:len(prices)], prices)
    
    fig = go.Figure(data=[go.Candlestick(
        x=df['date'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        increasing_line_color='green',
        increasing_fillcolor='green',
        decreasing_line_color='red',
        decreasing_fillcolor='red'
    )])
    
    # ネックライン（支持線）を追加
    neckline = base_price + 8
    fig.add_hline(y=neckline, line_dash="dash", line_color="blue",
                  annotation_text="支持線（ネックライン）", annotation_position="right")
    
    # 抵抗線を追加
    resistance_line = base_price + 20
    fig.add_hline(y=resistance_line, line_dash="dash", line_color="red",
                  annotation_text="抵抗線", annotation_position="right")
    
    fig.update_layout(
        title="ダブルトップパターン",
        xaxis_rangeslider_visible=False,
        height=400,
        showlegend=False
    )
    
    return fig


def create_double_bottom_chart() -> go.Figure:
    """ダブルボトムのチャートを生成"""
    dates = pd.date_range(start='2024-01-01', periods=40, freq='D')
    
    base_price = 100
    prices = []
    
    # 下降トレンド
    for i in range(8):
        prices.append(base_price - i * 2.5)
    
    # 1つ目のボトム
    prices.append(base_price - 20)
    prices.append(base_price - 18)
    prices.append(base_price - 20)
    
    # 中間の高値
    for i in range(6):
        prices.append(base_price - 20 + i * 2)
    
    # 2つ目のボトム
    prices.append(base_price - 20)
    prices.append(base_price - 18)
    prices.append(base_price - 20)
    
    # ブレイクアウト
    for i in range(10):
        prices.append(base_price - 20 + i * 1.5)
    
    df = create_ohlc_from_prices(dates[:len(prices)], prices)
    
    fig = go.Figure(data=[go.Candlestick(
        x=df['date'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        increasing_line_color='green',
        increasing_fillcolor='green',
        decreasing_line_color='red',
        decreasing_fillcolor='red'
    )])
    
    # ネックライン（抵抗線）を追加
    neckline = base_price - 8
    fig.add_hline(y=neckline, line_dash="dash", line_color="red",
                  annotation_text="抵抗線（ネックライン）", annotation_position="right")
    
    # 支持線を追加
    support_line = base_price - 20
    fig.add_hline(y=support_line, line_dash="dash", line_color="blue",
                  annotation_text="支持線", annotation_position="right")
    
    fig.update_layout(
        title="ダブルボトムパターン",
        xaxis_rangeslider_visible=False,
        height=400,
        showlegend=False
    )
    
    return fig


def create_inverse_head_shoulders_chart() -> go.Figure:
    """逆三尊のチャートを生成"""
    dates = pd.date_range(start='2024-01-01', periods=45, freq='D')
    
    base_price = 100
    prices = []
    
    # 下降トレンド
    for i in range(5):
        prices.append(base_price - i * 2)
    
    # 左肩
    prices.append(base_price - 10)
    prices.append(base_price - 8)
    prices.append(base_price - 10)
    
    # 中間の高値
    for i in range(4):
        prices.append(base_price - 10 + i * 1.5)
    
    # 頭（最も低い）
    prices.append(base_price - 15)
    prices.append(base_price - 13)
    prices.append(base_price - 15)
    
    # 中間の高値
    for i in range(4):
        prices.append(base_price - 15 + i * 1.5)
    
    # 右肩
    prices.append(base_price - 10)
    prices.append(base_price - 8)
    prices.append(base_price - 10)
    
    # ブレイクアウト
    for i in range(15):
        prices.append(base_price - 10 + i * 1.2)
    
    df = create_ohlc_from_prices(dates[:len(prices)], prices)
    
    fig = go.Figure(data=[go.Candlestick(
        x=df['date'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        increasing_line_color='green',
        increasing_fillcolor='green',
        decreasing_line_color='red',
        decreasing_fillcolor='red'
    )])
    
    # ネックライン（抵抗線）を追加
    neckline = base_price - 4
    fig.add_hline(y=neckline, line_dash="dash", line_color="red",
                  annotation_text="抵抗線（ネックライン）", annotation_position="right")
    
    # 支持線を追加
    support_line = base_price - 15
    fig.add_hline(y=support_line, line_dash="dash", line_color="blue",
                  annotation_text="支持線（頭）", annotation_position="right")
    
    fig.update_layout(
        title="逆三尊パターン",
        xaxis_rangeslider_visible=False,
        height=400,
        showlegend=False
    )
    
    return fig


def create_head_shoulders_chart() -> go.Figure:
    """三尊天井のチャートを生成"""
    dates = pd.date_range(start='2024-01-01', periods=45, freq='D')
    
    base_price = 100
    prices = []
    
    # 上昇トレンド
    for i in range(5):
        prices.append(base_price + i * 2)
    
    # 左肩
    prices.append(base_price + 10)
    prices.append(base_price + 8)
    prices.append(base_price + 10)
    
    # 中間の安値
    for i in range(4):
        prices.append(base_price + 10 - i * 1.5)
    
    # 頭（最も高い）
    prices.append(base_price + 15)
    prices.append(base_price + 13)
    prices.append(base_price + 15)
    
    # 中間の安値
    for i in range(4):
        prices.append(base_price + 15 - i * 1.5)
    
    # 右肩
    prices.append(base_price + 10)
    prices.append(base_price + 8)
    prices.append(base_price + 10)
    
    # ブレイクダウン
    for i in range(15):
        prices.append(base_price + 10 - i * 1.2)
    
    df = create_ohlc_from_prices(dates[:len(prices)], prices)
    
    fig = go.Figure(data=[go.Candlestick(
        x=df['date'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        increasing_line_color='green',
        increasing_fillcolor='green',
        decreasing_line_color='red',
        decreasing_fillcolor='red'
    )])
    
    # ネックライン（支持線）を追加
    neckline = base_price + 4
    fig.add_hline(y=neckline, line_dash="dash", line_color="blue",
                  annotation_text="支持線（ネックライン）", annotation_position="right")
    
    # 抵抗線を追加
    resistance_line = base_price + 15
    fig.add_hline(y=resistance_line, line_dash="dash", line_color="red",
                  annotation_text="抵抗線（頭）", annotation_position="right")
    
    fig.update_layout(
        title="三尊天井パターン",
        xaxis_rangeslider_visible=False,
        height=400,
        showlegend=False
    )
    
    return fig


def create_ascending_range_chart() -> go.Figure:
    """上昇レンジのチャートを生成"""
    dates = pd.date_range(start='2024-01-01', periods=35, freq='D')
    
    base_price = 100
    prices = []
    
    # 上昇トレンド
    for i in range(5):
        prices.append(base_price + i * 3)
    
    # レンジ内での上下動
    for cycle in range(3):
        for i in range(3):
            prices.append(base_price + 15 + cycle * 2 + i * 1.5)
        for i in range(3):
            prices.append(base_price + 20 + cycle * 2 - i * 1.5)
    
    # ブレイクアウト
    for i in range(8):
        prices.append(base_price + 25 + i * 2)
    
    df = create_ohlc_from_prices(dates[:len(prices)], prices)
    
    fig = go.Figure(data=[go.Candlestick(
        x=df['date'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        increasing_line_color='green',
        increasing_fillcolor='green',
        decreasing_line_color='red',
        decreasing_fillcolor='red'
    )])
    
    # 抵抗線を追加
    resistance_line = base_price + 25
    fig.add_hline(y=resistance_line, line_dash="dash", line_color="red",
                  annotation_text="抵抗線", annotation_position="right")
    
    # 支持線を追加
    support_line = base_price + 15
    fig.add_hline(y=support_line, line_dash="dash", line_color="blue",
                  annotation_text="支持線", annotation_position="right")
    
    fig.update_layout(
        title="上昇レンジパターン",
        xaxis_rangeslider_visible=False,
        height=400,
        showlegend=False
    )
    
    return fig


def create_descending_range_chart() -> go.Figure:
    """下降レンジのチャートを生成"""
    dates = pd.date_range(start='2024-01-01', periods=35, freq='D')
    
    base_price = 100
    prices = []
    
    # 下降トレンド
    for i in range(5):
        prices.append(base_price - i * 3)
    
    # レンジ内での上下動
    for cycle in range(3):
        for i in range(3):
            prices.append(base_price - 15 - cycle * 2 - i * 1.5)
        for i in range(3):
            prices.append(base_price - 20 - cycle * 2 + i * 1.5)
    
    # ブレイクダウン
    for i in range(8):
        prices.append(base_price - 25 - i * 2)
    
    df = create_ohlc_from_prices(dates[:len(prices)], prices)
    
    fig = go.Figure(data=[go.Candlestick(
        x=df['date'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        increasing_line_color='green',
        increasing_fillcolor='green',
        decreasing_line_color='red',
        decreasing_fillcolor='red'
    )])
    
    # 抵抗線を追加
    resistance_line = base_price - 15
    fig.add_hline(y=resistance_line, line_dash="dash", line_color="red",
                  annotation_text="抵抗線", annotation_position="right")
    
    # 支持線を追加
    support_line = base_price - 25
    fig.add_hline(y=support_line, line_dash="dash", line_color="blue",
                  annotation_text="支持線", annotation_position="right")
    
    fig.update_layout(
        title="下降レンジパターン",
        xaxis_rangeslider_visible=False,
        height=400,
        showlegend=False
    )
    
    return fig


def create_ascending_triangle_chart() -> go.Figure:
    """上昇三角持ち合いのチャートを生成"""
    dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
    
    base_price = 100
    prices = []
    
    # 上昇トレンド
    for i in range(5):
        prices.append(base_price + i * 2)
    
    # 三角形の形成（上限は水平、下限は上昇）
    upper = base_price + 15
    lower = base_price + 5
    
    for i in range(15):
        cycle_price = lower + (upper - lower) * (1 - i / 15)
        prices.append(cycle_price + np.random.uniform(-1, 1))
        lower += 0.3  # 下限が上昇
    
    # ブレイクアウト
    for i in range(5):
        prices.append(upper + i * 2)
    
    df = create_ohlc_from_prices(dates[:len(prices)], prices)
    
    fig = go.Figure(data=[go.Candlestick(
        x=df['date'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        increasing_line_color='green',
        increasing_fillcolor='green',
        decreasing_line_color='red',
        decreasing_fillcolor='red'
    )])
    
    # 抵抗線（上限）を追加
    fig.add_hline(y=upper, line_dash="dash", line_color="red",
                  annotation_text="抵抗線（上限）", annotation_position="right")
    
    # 支持線（下限）を追加
    fig.add_hline(y=lower, line_dash="dash", line_color="blue",
                  annotation_text="支持線（下限）", annotation_position="right")
    
    fig.update_layout(
        title="上昇三角持ち合いパターン",
        xaxis_rangeslider_visible=False,
        height=400,
        showlegend=False
    )
    
    return fig


def create_descending_triangle_chart() -> go.Figure:
    """下降三角持ち合いのチャートを生成"""
    dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
    
    base_price = 100
    prices = []
    
    # 下降トレンド
    for i in range(5):
        prices.append(base_price - i * 2)
    
    # 三角形の形成（下限は水平、上限は下降）
    upper = base_price - 5
    lower = base_price - 15
    
    for i in range(15):
        cycle_price = lower + (upper - lower) * (1 - i / 15)
        prices.append(cycle_price + np.random.uniform(-1, 1))
        upper -= 0.3  # 上限が下降
    
    # ブレイクダウン
    for i in range(5):
        prices.append(lower - i * 2)
    
    df = create_ohlc_from_prices(dates[:len(prices)], prices)
    
    fig = go.Figure(data=[go.Candlestick(
        x=df['date'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        increasing_line_color='green',
        increasing_fillcolor='green',
        decreasing_line_color='red',
        decreasing_fillcolor='red'
    )])
    
    # 支持線（下限）を追加
    fig.add_hline(y=lower, line_dash="dash", line_color="blue",
                  annotation_text="支持線（下限）", annotation_position="right")
    
    # 抵抗線（上限）を追加
    fig.add_hline(y=upper, line_dash="dash", line_color="red",
                  annotation_text="抵抗線（上限）", annotation_position="right")
    
    fig.update_layout(
        title="下降三角持ち合いパターン",
        xaxis_rangeslider_visible=False,
        height=400,
        showlegend=False
    )
    
    return fig


def create_bullish_flag_chart() -> go.Figure:
    """上昇フラッグのチャートを生成"""
    dates = pd.date_range(start='2024-01-01', periods=25, freq='D')
    
    base_price = 100
    prices = []
    
    # 強い上昇（旗竿）
    for i in range(8):
        prices.append(base_price + i * 3)
    
    # フラッグ（短期的な調整）
    for i in range(8):
        prices.append(base_price + 24 - i * 0.5 + np.random.uniform(-1, 1))
    
    # ブレイクアウト
    for i in range(5):
        prices.append(base_price + 20 + i * 2.5)
    
    df = create_ohlc_from_prices(dates[:len(prices)], prices)
    
    fig = go.Figure(data=[go.Candlestick(
        x=df['date'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        increasing_line_color='green',
        increasing_fillcolor='green',
        decreasing_line_color='red',
        decreasing_fillcolor='red'
    )])
    
    # 抵抗線を追加（フラッグの上限）
    resistance_line = base_price + 24
    fig.add_hline(y=resistance_line, line_dash="dash", line_color="red",
                  annotation_text="抵抗線", annotation_position="right")
    
    # 支持線を追加（フラッグの下限）
    support_line = base_price + 20
    fig.add_hline(y=support_line, line_dash="dash", line_color="blue",
                  annotation_text="支持線", annotation_position="right")
    
    fig.update_layout(
        title="上昇フラッグパターン",
        xaxis_rangeslider_visible=False,
        height=400,
        showlegend=False
    )
    
    return fig


def create_bearish_flag_chart() -> go.Figure:
    """下降フラッグのチャートを生成"""
    dates = pd.date_range(start='2024-01-01', periods=25, freq='D')
    
    base_price = 100
    prices = []
    
    # 強い下降（旗竿）
    for i in range(8):
        prices.append(base_price - i * 3)
    
    # フラッグ（短期的な調整）
    for i in range(8):
        prices.append(base_price - 24 + i * 0.5 + np.random.uniform(-1, 1))
    
    # ブレイクダウン
    for i in range(5):
        prices.append(base_price - 20 - i * 2.5)
    
    df = create_ohlc_from_prices(dates[:len(prices)], prices)
    
    fig = go.Figure(data=[go.Candlestick(
        x=df['date'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        increasing_line_color='green',
        increasing_fillcolor='green',
        decreasing_line_color='red',
        decreasing_fillcolor='red'
    )])
    
    # 抵抗線を追加（フラッグの上限）
    resistance_line = base_price - 20
    fig.add_hline(y=resistance_line, line_dash="dash", line_color="red",
                  annotation_text="抵抗線", annotation_position="right")
    
    # 支持線を追加（フラッグの下限）
    support_line = base_price - 24
    fig.add_hline(y=support_line, line_dash="dash", line_color="blue",
                  annotation_text="支持線", annotation_position="right")
    
    fig.update_layout(
        title="下降フラッグパターン",
        xaxis_rangeslider_visible=False,
        height=400,
        showlegend=False
    )
    
    return fig


def create_bullish_pennant_chart() -> go.Figure:
    """上昇ペナントのチャートを生成"""
    dates = pd.date_range(start='2024-01-01', periods=25, freq='D')
    
    base_price = 100
    prices = []
    
    # 強い上昇（旗竿）
    for i in range(8):
        prices.append(base_price + i * 3)
    
    # ペナント（三角形の調整）
    upper = base_price + 24
    lower = base_price + 20
    
    for i in range(8):
        cycle_price = lower + (upper - lower) * (1 - i / 8)
        prices.append(cycle_price + np.random.uniform(-0.5, 0.5))
        upper -= 0.2
        lower += 0.2
    
    # ブレイクアウト
    for i in range(5):
        prices.append(base_price + 22 + i * 2.5)
    
    df = create_ohlc_from_prices(dates[:len(prices)], prices)
    
    fig = go.Figure(data=[go.Candlestick(
        x=df['date'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        increasing_line_color='green',
        increasing_fillcolor='green',
        decreasing_line_color='red',
        decreasing_fillcolor='red'
    )])
    
    # 抵抗線を追加（ペナントの上限）
    resistance_line = base_price + 24
    fig.add_hline(y=resistance_line, line_dash="dash", line_color="red",
                  annotation_text="抵抗線", annotation_position="right")
    
    # 支持線を追加（ペナントの下限）
    support_line = base_price + 20
    fig.add_hline(y=support_line, line_dash="dash", line_color="blue",
                  annotation_text="支持線", annotation_position="right")
    
    fig.update_layout(
        title="上昇ペナントパターン",
        xaxis_rangeslider_visible=False,
        height=400,
        showlegend=False
    )
    
    return fig


def create_bearish_pennant_chart() -> go.Figure:
    """下降ペナントのチャートを生成"""
    dates = pd.date_range(start='2024-01-01', periods=25, freq='D')
    
    base_price = 100
    prices = []
    
    # 強い下降（旗竿）
    for i in range(8):
        prices.append(base_price - i * 3)
    
    # ペナント（三角形の調整）
    upper = base_price - 20
    lower = base_price - 24
    
    for i in range(8):
        cycle_price = lower + (upper - lower) * (1 - i / 8)
        prices.append(cycle_price + np.random.uniform(-0.5, 0.5))
        upper -= 0.2
        lower += 0.2
    
    # ブレイクダウン
    for i in range(5):
        prices.append(base_price - 22 - i * 2.5)
    
    df = create_ohlc_from_prices(dates[:len(prices)], prices)
    
    fig = go.Figure(data=[go.Candlestick(
        x=df['date'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        increasing_line_color='green',
        increasing_fillcolor='green',
        decreasing_line_color='red',
        decreasing_fillcolor='red'
    )])
    
    # 抵抗線を追加（ペナントの上限）
    resistance_line = base_price - 20
    fig.add_hline(y=resistance_line, line_dash="dash", line_color="red",
                  annotation_text="抵抗線", annotation_position="right")
    
    # 支持線を追加（ペナントの下限）
    support_line = base_price - 24
    fig.add_hline(y=support_line, line_dash="dash", line_color="blue",
                  annotation_text="支持線", annotation_position="right")
    
    fig.update_layout(
        title="下降ペナントパターン",
        xaxis_rangeslider_visible=False,
        height=400,
        showlegend=False
    )
    
    return fig


def create_rising_wedge_chart() -> go.Figure:
    """上昇ウェッジのチャートを生成"""
    dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
    
    base_price = 100
    prices = []
    
    # 上昇しながら収束
    upper_start = base_price + 5
    lower_start = base_price - 5
    
    for i in range(20):
        upper = upper_start + i * 0.5
        lower = lower_start + i * 1.5
        cycle_price = lower + (upper - lower) * 0.6
        prices.append(cycle_price + np.random.uniform(-0.5, 0.5))
    
    # ブレイクダウン
    for i in range(5):
        prices.append(base_price + 15 - i * 2)
    
    df = create_ohlc_from_prices(dates[:len(prices)], prices)
    
    fig = go.Figure(data=[go.Candlestick(
        x=df['date'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        increasing_line_color='green',
        increasing_fillcolor='green',
        decreasing_line_color='red',
        decreasing_fillcolor='red'
    )])
    
    # 抵抗線を追加（ウェッジの上限）
    resistance_line = base_price + 15
    fig.add_hline(y=resistance_line, line_dash="dash", line_color="red",
                  annotation_text="抵抗線", annotation_position="right")
    
    # 支持線を追加（ウェッジの下限）
    support_line = base_price + 5
    fig.add_hline(y=support_line, line_dash="dash", line_color="blue",
                  annotation_text="支持線", annotation_position="right")
    
    fig.update_layout(
        title="上昇ウェッジパターン",
        xaxis_rangeslider_visible=False,
        height=400,
        showlegend=False
    )
    
    return fig


def create_falling_wedge_chart() -> go.Figure:
    """下降ウェッジのチャートを生成"""
    dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
    
    base_price = 100
    prices = []
    
    # 下降しながら収束
    upper_start = base_price + 5
    lower_start = base_price - 5
    
    for i in range(20):
        upper = upper_start - i * 1.5
        lower = lower_start - i * 0.5
        cycle_price = lower + (upper - lower) * 0.4
        prices.append(cycle_price + np.random.uniform(-0.5, 0.5))
    
    # ブレイクアウト
    for i in range(5):
        prices.append(base_price - 15 + i * 2)
    
    df = create_ohlc_from_prices(dates[:len(prices)], prices)
    
    fig = go.Figure(data=[go.Candlestick(
        x=df['date'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        increasing_line_color='green',
        increasing_fillcolor='green',
        decreasing_line_color='red',
        decreasing_fillcolor='red'
    )])
    
    # 抵抗線を追加（ウェッジの上限）
    resistance_line = base_price - 5
    fig.add_hline(y=resistance_line, line_dash="dash", line_color="red",
                  annotation_text="抵抗線", annotation_position="right")
    
    # 支持線を追加（ウェッジの下限）
    support_line = base_price - 15
    fig.add_hline(y=support_line, line_dash="dash", line_color="blue",
                  annotation_text="支持線", annotation_position="right")
    
    fig.update_layout(
        title="下降ウェッジパターン",
        xaxis_rangeslider_visible=False,
        height=400,
        showlegend=False
    )
    
    return fig


def create_saucer_top_chart() -> go.Figure:
    """ソーサートップのチャートを生成"""
    dates = pd.date_range(start='2024-01-01', periods=40, freq='D')
    
    base_price = 100
    prices = []
    
    # 緩やかな上昇
    for i in range(10):
        prices.append(base_price + i * 1.5)
    
    # 円弧状の天井
    center = base_price + 15
    radius = 8
    
    for i in range(15):
        angle = np.pi * i / 15
        prices.append(center + radius * np.cos(angle) + np.random.uniform(-0.5, 0.5))
    
    # 緩やかな下降
    for i in range(10):
        prices.append(base_price + 15 - i * 1.5)
    
    df = create_ohlc_from_prices(dates[:len(prices)], prices)
    
    fig = go.Figure(data=[go.Candlestick(
        x=df['date'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        increasing_line_color='green',
        increasing_fillcolor='green',
        decreasing_line_color='red',
        decreasing_fillcolor='red'
    )])
    
    # 抵抗線を追加（天井）
    resistance_line = base_price + 15
    fig.add_hline(y=resistance_line, line_dash="dash", line_color="red",
                  annotation_text="抵抗線（天井）", annotation_position="right")
    
    # 支持線を追加（下降開始点）
    support_line = base_price + 5
    fig.add_hline(y=support_line, line_dash="dash", line_color="blue",
                  annotation_text="支持線", annotation_position="right")
    
    fig.update_layout(
        title="ソーサートップパターン",
        xaxis_rangeslider_visible=False,
        height=400,
        showlegend=False
    )
    
    return fig


def create_saucer_bottom_chart() -> go.Figure:
    """ソーサーボトムのチャートを生成"""
    dates = pd.date_range(start='2024-01-01', periods=40, freq='D')
    
    base_price = 100
    prices = []
    
    # 緩やかな下降
    for i in range(10):
        prices.append(base_price - i * 1.5)
    
    # 円弧状の底
    center = base_price - 15
    radius = 8
    
    for i in range(15):
        angle = np.pi + np.pi * i / 15
        prices.append(center + radius * np.cos(angle) + np.random.uniform(-0.5, 0.5))
    
    # 緩やかな上昇
    for i in range(10):
        prices.append(base_price - 15 + i * 1.5)
    
    df = create_ohlc_from_prices(dates[:len(prices)], prices)
    
    fig = go.Figure(data=[go.Candlestick(
        x=df['date'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        increasing_line_color='green',
        increasing_fillcolor='green',
        decreasing_line_color='red',
        decreasing_fillcolor='red'
    )])
    
    # 支持線を追加（底）
    support_line = base_price - 15
    fig.add_hline(y=support_line, line_dash="dash", line_color="blue",
                  annotation_text="支持線（底）", annotation_position="right")
    
    # 抵抗線を追加（上昇開始点）
    resistance_line = base_price - 5
    fig.add_hline(y=resistance_line, line_dash="dash", line_color="red",
                  annotation_text="抵抗線", annotation_position="right")
    
    fig.update_layout(
        title="ソーサーボトムパターン",
        xaxis_rangeslider_visible=False,
        height=400,
        showlegend=False
    )
    
    return fig


def create_default_chart() -> go.Figure:
    """デフォルトチャートを生成"""
    dates = pd.date_range(start='2024-01-01', periods=20, freq='D')
    prices = [100 + i * 2 + np.random.uniform(-2, 2) for i in range(20)]
    
    df = create_ohlc_from_prices(dates, prices)
    
    fig = go.Figure(data=[go.Candlestick(
        x=df['date'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        increasing_line_color='green',
        increasing_fillcolor='green',
        decreasing_line_color='red',
        decreasing_fillcolor='red'
    )])
    
    fig.update_layout(
        title="チャートパターン",
        xaxis_rangeslider_visible=False,
        height=400,
        showlegend=False
    )
    
    return fig


def create_ohlc_from_prices(dates: pd.DatetimeIndex, prices: list) -> pd.DataFrame:
    """
    価格リストからOHLCデータを生成
    
    Args:
        dates: 日付のインデックス
        prices: 価格のリスト
    
    Returns:
        OHLCデータを含むDataFrame
    """
    df = pd.DataFrame({
        'date': dates,
        'close': prices
    })
    
    # OHLCを生成（簡易版）
    df['open'] = df['close'].shift(1).fillna(df['close'].iloc[0])
    df['high'] = df[['open', 'close']].max(axis=1) + np.random.uniform(0, 2, len(df))
    df['low'] = df[['open', 'close']].min(axis=1) - np.random.uniform(0, 2, len(df))
    
    return df

