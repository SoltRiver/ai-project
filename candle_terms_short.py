"""
ローソク足 → 説明文（ホバー用）モジュール
ローソク足の種類から簡易説明文を取得する
"""

from typing import Optional
from candle_classify import classify_candle
from candlestick_terms_data import get_candlestick_term_info

# ローソク足の種類と用語辞典のカテゴリ・用語名のマッピング
CANDLE_TYPE_TO_TERM = {
    "十字線": ("ローソク足の基本形", "十字線"),
    "カラカサ": ("ローソク足の基本形", "カラカサ"),
    "トンカチ": ("ローソク足の基本形", "トンカチ"),
    "マルボウズ": ("ローソク足の基本形", "マルボウズ"),
    "大陽線": ("ローソク足の基本形", "大陽線"),
    "大陰線": ("ローソク足の基本形", "大陰線"),
    "陽線": ("ローソク足の基本形", "陽線"),
    "陰線": ("ローソク足の基本形", "陰線")
}


def get_candle_description(open_price: float, high_price: float,
                           low_price: float, close_price: float) -> str:
    """
    OHLCデータからローソク足の簡易説明文を取得（ホバー用）
    
    Args:
        open_price: 始値
        high_price: 高値
        low_price: 安値
        close_price: 終値
    
    Returns:
        ローソク足の簡易説明文
    """
    candle_type = classify_candle(open_price, high_price, low_price, close_price)
    
    # 用語辞典から説明を取得
    term_info = get_candle_term_info(candle_type)
    
    if term_info:
        return term_info.get("meaning", f"{candle_type}が形成されています。")
    else:
        return f"{candle_type}が形成されています。"


def get_candle_term_info(candle_type: str) -> dict:
    """
    ローソク足の種類から用語辞典の情報を取得
    
    Args:
        candle_type: ローソク足の種類
    
    Returns:
        用語辞典の情報（辞書）または空の辞書
    """
    if candle_type in CANDLE_TYPE_TO_TERM:
        category, term_name = CANDLE_TYPE_TO_TERM[candle_type]
        return get_candlestick_term_info(category, term_name)
    return {}


def get_candle_hover_text(date: str, open_price: float, high_price: float,
                          low_price: float, close_price: float,
                          volume: Optional[float] = None) -> str:
    """
    ホバー時に表示する完全なテキストを生成
    
    Args:
        date: 日付
        open_price: 始値
        high_price: 高値
        low_price: 安値
        close_price: 終値
        volume: 出来高（オプション）
    
    Returns:
        ホバー時に表示するテキスト
    """
    candle_type = classify_candle(open_price, high_price, low_price, close_price)
    description = get_candle_description(open_price, high_price, low_price, close_price)
    
    text = f"日付: {date}\n"
    text += f"始値: {open_price:.2f}\n"
    text += f"高値: {high_price:.2f}\n"
    text += f"安値: {low_price:.2f}\n"
    text += f"終値: {close_price:.2f}\n"
    
    if volume is not None:
        text += f"出来高: {volume:,.0f}\n"
    
    text += f"\n種類: {candle_type}\n"
    text += f"説明: {description}"
    
    return text
