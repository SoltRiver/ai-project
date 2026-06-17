"""
LangGraph: Stock News State
"""

from typing import Any, Dict, List, TypedDict


class StockNewsState(TypedDict, total=False):
    """
    ニュース要約ワークフローの状態（State）を管理する
    """

    stock_code: str  # 入力: 銘柄コード
    language: str  # 入力: 要約出力言語 (例: "日本語", "English")
    news_items: List[Dict[str, Any]]  # fetch_news の結果
    summaries: List[Dict[str, Any]]  # summarize_news の結果
    response: Dict[str, Any]  # build_response の結果（テンプレート描画用データ）
    error: str  # エラーメッセージ（あれば）
