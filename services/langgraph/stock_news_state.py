"""
LangGraph: Stock News State
"""

from typing import TypedDict, List, Dict, Any

class StockNewsState(TypedDict, total=False):
    """
    ニュース要約ワークフローの状態（State）を管理する
    """
    stock_code: str               # 入力: 銘柄コード
    news_items: List[Dict[str, Any]] # fetch_news の結果
    summaries: List[Dict[str, Any]]  # summarize_news の結果
    response: Dict[str, Any]      # build_response の結果（テンプレート描画用データ）
    error: str                    # エラーメッセージ（あれば）
