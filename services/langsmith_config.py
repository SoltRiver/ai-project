"""
LangSmith トレース設定モジュール

LangSmith のトレース設定・メタデータ構築・APIキーマスキング処理を
一元管理する。各サービスからインポートして使用する。

環境変数:
    LANGCHAIN_TRACING_V2: トレース有効化 ("true" で有効)
    LANGSMITH_TRACING: トレース有効化 (新しい推奨名)
    LANGCHAIN_API_KEY: LangSmith API キー
    LANGCHAIN_PROJECT: デフォルトプロジェクト名
    LANGCHAIN_ENDPOINT: LangSmith エンドポイントURL
"""

import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# .envファイルから環境変数をロード
load_dotenv()

# ====================================================================
# マスキング対象パターン
# APIキー・個人情報等がトレースに記録されることを防ぐ
# ====================================================================

# APIキーの典型的なパターン（sk-xxx, AIza, lsv2_ など）
_SENSITIVE_PATTERNS = [
    re.compile(r"(sk-[a-zA-Z0-9\-_]{20,})"),  # OpenAI APIキー
    re.compile(r"(AIza[a-zA-Z0-9\-_]{30,})"),  # Google APIキー
    re.compile(r"(lsv2_[a-zA-Z0-9_]{20,})"),  # LangSmith APIキー
    re.compile(r"(Bearer\s+[a-zA-Z0-9\-_.]+)"),  # Bearer トークン
]

# マスキング対象のキー名（辞書内の値をマスクする）
_SENSITIVE_KEYS = {
    "api_key",
    "apikey",
    "api_secret",
    "password",
    "token",
    "secret",
    "authorization",
    "openai_api_key",
    "google_api_key",
    "langchain_api_key",
    "langsmith_api_key",
}


def is_tracing_enabled() -> bool:
    """
    LangSmithトレースが有効かどうかを判定する。

    LANGCHAIN_TRACING_V2 または LANGSMITH_TRACING が "true" の場合に有効。

    Returns:
        トレースが有効なら True
    """
    v2 = os.getenv("LANGCHAIN_TRACING_V2", "").lower() == "true"
    new = os.getenv("LANGSMITH_TRACING", "").lower() == "true"
    return v2 or new


def get_langsmith_project(feature: Optional[str] = None) -> str:
    """
    LangSmithプロジェクト名を取得する。

    機能名が指定された場合は、ベースプロジェクト名に機能名を付加する。
    ただし、デフォルトではLANGCHAIN_PROJECT環境変数の値をそのまま使用する。

    Args:
        feature: 機能名 (例: "rag", "agent", "evaluation")
                 Noneの場合はデフォルトプロジェクトを返す

    Returns:
        プロジェクト名文字列
    """
    base = os.getenv("LANGCHAIN_PROJECT", "stock-analysis-dev")
    if feature:
        return f"stock-analysis-{feature}"
    return base


def configure_langsmith() -> None:
    """
    LangSmithの設定を初期化する。

    アプリケーション起動時に一度呼び出すことで、
    環境変数の状態をログに記録する。
    """
    if is_tracing_enabled():
        project = get_langsmith_project()
        endpoint = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
        # APIキーの先頭4文字のみ表示（セキュリティ考慮）
        api_key = os.getenv("LANGCHAIN_API_KEY", "")
        masked_key = f"{api_key[:4]}****" if len(api_key) > 4 else "未設定"

        logger.info(
            "LangSmith トレース有効: "
            f"project={project}, "
            f"endpoint={endpoint}, "
            f"api_key={masked_key}"
        )
    else:
        logger.info("LangSmith トレース無効")


def build_trace_metadata(
    feature: str,
    prompt_version: str = "v1",
    prompt_name: Optional[str] = None,
    model: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    LangSmithトレース用の標準メタデータ辞書を構築する。

    各処理から呼び出し、一貫したメタデータ構造を保証する。

    Args:
        feature: 機能名 (例: "news_summary", "rag", "agent")
        prompt_version: プロンプトバージョン (例: "v1", "v2")
        prompt_name: プロンプト名 (省略時はfeatureと同じ)
        model: 使用モデル名
        **kwargs: 追加メタデータ (symbol, retriever, top_k 等)

    Returns:
        メタデータ辞書
    """
    metadata = {
        "feature": feature,
        "source": "stock_app",
        "prompt_name": prompt_name or feature,
        "prompt_version": prompt_version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if model:
        metadata["model"] = model

    # 追加メタデータをマージ（機密情報はマスク）
    for key, value in kwargs.items():
        if key.lower() in _SENSITIVE_KEYS:
            continue
        metadata[key] = value

    return metadata


def build_trace_config(
    tags: List[str],
    metadata: Dict[str, Any],
    run_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    LangChain/LangGraph の invoke/ainvoke に渡す config 辞書を構築する。

    Args:
        tags: タグのリスト (例: ["news_summary", "langgraph"])
        metadata: メタデータ辞書 (build_trace_metadata で生成)
        run_name: 実行名（LangSmith UIに表示される名前）

    Returns:
        configurable パラメータを含む config 辞書
    """
    config: Dict[str, Any] = {
        "tags": tags,
        "metadata": metadata,
    }
    if run_name:
        config["run_name"] = run_name
    return config


def mask_sensitive_data(data: Any) -> Any:
    """
    APIキー・個人情報などの機密データをマスキングする。

    辞書やリストを再帰的に処理し、機密キーの値や
    APIキーパターンにマッチする文字列を「****」に置換する。

    Args:
        data: マスキング対象のデータ

    Returns:
        マスキング済みのデータ（元データは変更しない）
    """
    if isinstance(data, dict):
        masked = {}
        for key, value in data.items():
            if key.lower() in _SENSITIVE_KEYS:
                masked[key] = "****"
            else:
                masked[key] = mask_sensitive_data(value)
        return masked

    elif isinstance(data, list):
        return [mask_sensitive_data(item) for item in data]

    elif isinstance(data, str):
        result = data
        for pattern in _SENSITIVE_PATTERNS:
            result = pattern.sub("****", result)
        return result

    return data
