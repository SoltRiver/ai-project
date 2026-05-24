"""
LangChainチェーンパッケージ
各種LLMチェーン（ニュース要約、分析等）を定義する。
プロンプト定義は ai/prompts に分離されている。
"""

from ai.chains.news_summarizer import summarize_news_article, summarize_news_batch
