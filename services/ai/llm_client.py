"""
LLMクライアントファクトリー

OpenAI / Gemini などのLLMクライアントを一元管理し、
LangChainやLangGraphの各ノードから共通で利用できるようにする。
"""

import logging
import os
from typing import Optional

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# .envファイルから環境変数をロード
load_dotenv()


def get_chat_model(provider: str = "openai", model_name: Optional[str] = None):
    """
    指定されたプロバイダのChatModelインスタンスを返す。

    Args:
        provider: "openai" または "google"
        model_name: 使用するモデル名（指定がない場合はデフォルト値を使用）

    Returns:
        BaseChatModel
    """
    timeout = 10.0  # API呼び出しのタイムアウト秒数（Geminiの制限により最低10秒が必要）
    max_retries = 1  # クォータ制限などのエラー発生時に何度もリトライしてフリーズするのを防ぐため、リトライ回数を制限

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model_name or "gpt-4o-mini",
            temperature=0.3,
            api_key=os.getenv("OPENAI_API_KEY"),
            timeout=timeout,
            max_retries=max_retries,
        )
    elif provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        # デフォルトをgemini-2.0-flashに変更（1.5-flashは廃止）
        return ChatGoogleGenerativeAI(
            model=model_name or "gemini-2.0-flash",
            temperature=0.3,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            timeout=timeout,
            max_retries=max_retries,
        )
    else:
        raise ValueError(f"Unknown provider: {provider}")


def get_default_model_name(
    provider: str = "openai", model_name: Optional[str] = None
) -> str:
    """
    指定されたプロバイダのデフォルトモデル名を返す。

    トレースメタデータにモデル名を記録するためのヘルパー。

    Args:
        provider: "openai" または "google"
        model_name: 明示的に指定されたモデル名

    Returns:
        実際に使用されるモデル名
    """
    if model_name:
        return model_name
    if provider == "openai":
        return "gpt-4o-mini"
    elif provider == "google":
        return "gemini-2.0-flash"
    return f"unknown-{provider}"
