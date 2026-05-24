"""
LLMクライアントファクトリー

OpenAI / Gemini などのLLMクライアントを一元管理し、
LangChainやLangGraphの各ノードから共通で利用できるようにする。
"""

import os
import logging
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
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model_name or "gpt-4o-mini",
            temperature=0.3,
            api_key=os.getenv("OPENAI_API_KEY")
        )
    elif provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        # デフォルトをgemini-2.0-flashに変更（1.5-flashは廃止）
        return ChatGoogleGenerativeAI(
            model=model_name or "gemini-2.0-flash",
            temperature=0.3,
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )
    else:
        raise ValueError(f"Unknown provider: {provider}")
