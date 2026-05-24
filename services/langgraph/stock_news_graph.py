"""
LangGraph: Stock News Workflow Graph
"""

import logging
from typing import Dict, Any

from langgraph.graph import StateGraph, START, END

from services.langgraph.stock_news_state import StockNewsState
from services.langgraph.stock_news_nodes import (
    fetch_news_node,
    summarize_news_node,
    classify_sentiment_node,
    build_response_node
)

logger = logging.getLogger(__name__)

def create_stock_news_graph():
    """
    ニュース要約ワークフローのGraphを構築してコンパイルする。
    """
    # 1. グラフの初期化 (State定義を渡す)
    workflow = StateGraph(StockNewsState)

    # 2. ノードの追加
    workflow.add_node("fetch_news", fetch_news_node)
    workflow.add_node("summarize_news", summarize_news_node)
    workflow.add_node("classify_sentiment", classify_sentiment_node)
    workflow.add_node("build_response", build_response_node)

    # 3. エッジの接続 (フローの定義)
    workflow.add_edge(START, "fetch_news")
    
    # 簡単な条件分岐を追加
    # fetch_news でエラーが出た場合は END へ直行
    def check_fetch_error(state: StockNewsState) -> str:
        if "error" in state:
            return "end"
        return "continue"
    
    workflow.add_conditional_edges(
        "fetch_news",
        check_fetch_error,
        {
            "continue": "summarize_news",
            "end": END
        }
    )

    # summarize_news でもエラー分岐
    def check_summarize_error(state: StockNewsState) -> str:
        if "error" in state:
            return "end"
        return "continue"

    workflow.add_conditional_edges(
        "summarize_news",
        check_summarize_error,
        {
            "continue": "classify_sentiment",
            "end": END
        }
    )

    workflow.add_edge("classify_sentiment", "build_response")
    workflow.add_edge("build_response", END)

    # 4. コンパイルして実行可能なアプリにする
    app = workflow.compile()
    return app


# シングルトンとしてグラフインスタンスを保持
_news_graph_app = None

def get_news_graph():
    global _news_graph_app
    if _news_graph_app is None:
        _news_graph_app = create_stock_news_graph()
    return _news_graph_app


def run_stock_news_workflow(stock_code: str) -> Dict[str, Any]:
    """
    外部からグラフを実行するための公開関数。
    """
    logger.info(f"Starting news workflow for {stock_code}")
    try:
        app = get_news_graph()
        initial_state = {"stock_code": stock_code}
        
        # graph.invoke() で同期実行
        final_state = app.invoke(initial_state)
        return final_state
        
    except Exception as e:
        logger.error(f"Workflow execution failed: {e}")
        return {"error": f"システムエラーが発生しました: {e}"}
