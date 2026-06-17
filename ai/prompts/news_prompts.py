"""
ニュース要約用プロンプト定義

チェーン (ai/chains/news_summarizer.py) から使用されるプロンプトテンプレートと
出力スキーマ（Pydantic モデル）を定義する。

プロンプトの改訂時はこのファイルのみを変更すればよく、
チェーンロジックに影響を与えない。
"""

from typing import List

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

# ====================================================================
# 出力スキーマ定義（Pydantic）
# LLMの出力をバリデーションするための型定義。
# チェーン側の JsonOutputParser に渡して構造を強制する。
# ====================================================================


class ImpactedStock(BaseModel):
    """影響銘柄の情報"""

    name: str = Field(
        description="銘柄名または業種名（例: トヨタ自動車、半導体セクター）"
    )
    impact_type: str = Field(description="影響タイプ: 'positive' または 'negative'")
    reason: str = Field(description="影響の理由（指定された言語、1〜2文）")


class NewsSummaryOutput(BaseModel):
    """ニュース要約の出力スキーマ"""

    translated_title: str = Field(
        description="ニュース記事タイトルの指定された言語への自然な翻訳"
    )
    summarized_content: str = Field(
        description="初心者向けの80文字以内の要約（指定された言語）"
    )
    sentiment: str = Field(
        description="センチメント: 'positive', 'negative', 'neutral' のいずれか"
    )
    sentiment_reason: str = Field(
        description="センチメント判定の理由（指定された言語、1〜2文）"
    )
    impacted_stocks: List[ImpactedStock] = Field(
        description="このニュースが影響を与える可能性のある銘柄リスト",
        default_factory=list,
    )


# ====================================================================
# プロンプトテンプレート文字列
# ====================================================================

# システムプロンプト: 金融アナリストとしての役割設定
# {format_instructions} はチェーン側で JsonOutputParser から注入される
NEWS_SUMMARY_SYSTEM_PROMPT = """あなたは熟練した金融市場アナリストです。
以下のルールに従って、ニュース記事を分析してください。

## ルール
1. すべての出力（翻訳タイトル、要約、センチメント判定の理由、影響銘柄の理由など）は {language} で記述すること。
2. 元記事がどのような言語であっても、必ず指定された言語 {language} に翻訳・要約すること。
3. 要約は株式投資初心者にも分かりやすく、80文字以内を目標とすること。
4. センチメントは株式市場全体への影響を基準に判定すること。
5. 影響銘柄は具体的な企業名またはセクター名で記載すること。
6. 出力は必ず指定されたJSON形式で返すこと。

{format_instructions}"""

# ユーザープロンプト: 記事データの入力テンプレート
NEWS_SUMMARY_USER_PROMPT = """以下のニュース記事を分析してください。

【記事タイトル】
{title}

【配信元】
{publisher}

【記事本文】
{body}

上記の記事について、JSON形式で分析結果を出力してください。"""


# ====================================================================
# プロンプトテンプレート構築ヘルパー
# ====================================================================


def build_news_summary_prompt() -> ChatPromptTemplate:
    """
    ニュース要約用の ChatPromptTemplate を構築して返す。

    チェーン側で .partial(format_instructions=...) を呼び出して
    出力フォーマット指示を注入してから使用する。

    Returns:
        ChatPromptTemplate: system + human メッセージのテンプレート
    """
    return ChatPromptTemplate.from_messages(
        [
            ("system", NEWS_SUMMARY_SYSTEM_PROMPT),
            ("human", NEWS_SUMMARY_USER_PROMPT),
        ]
    )
