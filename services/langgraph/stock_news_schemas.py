"""
LangGraph: Stock News Validation Schemas
"""

from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator


class StockNewsInput(BaseModel):
    """
    入力パラメータのバリデーションモデル。
    """

    stock_code: str = Field(..., description="銘柄コード")
    language: str = Field(default="日本語", description="要約出力言語")

    @field_validator("stock_code")
    @classmethod
    def validate_stock_code(cls, v: str) -> str:
        # 銘柄コードの前後空白をトリムし、空文字でないことを確認
        v = v.strip()
        if not v:
            raise ValueError("銘柄コードは空にできません。")
        return v


class NewsItem(BaseModel):
    """
    取得された個別ニュースのバリデーションモデル。
    """

    title: str = Field(..., description="ニュースのタイトル")
    publisher: str = Field(default="-", description="配信元")
    link: str = Field(default="#", description="ニュースのリンクURL")
    published_at: str = Field(default="", description="配信日時")
    summary: str = Field(default="-", description="ニュースの要約 (取得時のもの)")

    @field_validator(
        "title", "publisher", "link", "published_at", "summary", mode="before"
    )
    @classmethod
    def check_empty_or_none(cls, v: Any) -> str:
        # edit-rules: 値が取得できなかった場合は、NoneやNullなどにせずにーや-でセット
        if v is None:
            return "-"
        s = str(v).strip()
        if not s:
            return "-"
        return s

    @field_validator("link", mode="before")
    @classmethod
    def check_link(cls, v: Any) -> str:
        # URLリンクが取得できなかった場合は、プレースホルダーとして '#' をセット
        if v is None:
            return "#"
        s = str(v).strip()
        if not s:
            return "#"
        return s


class AISummaryResult(BaseModel):
    """
    LLMによる要約とセンチメント判定結果のバリデーションモデル。
    """

    translated_title: Optional[str] = Field(default=None, description="翻訳タイトル")
    summarized_content: str = Field(..., description="要約されたコンテンツ")
    sentiment: str = Field(
        default="neutral", description="センチメント (positive, negative, neutral)"
    )
    sentiment_reason: str = Field(default="-", description="センチメントの判定理由")
    impacted_stocks: List[str] = Field(
        default_factory=list, description="影響を受ける銘柄コード"
    )

    @field_validator("sentiment")
    @classmethod
    def validate_sentiment(cls, v: str) -> str:
        # センチメント文字列をトリム・小文字化し、有効な値でなければ neutral にフォールバック
        v = v.strip().lower()
        if v not in ["positive", "negative", "neutral"]:
            return "neutral"
        return v

    @field_validator("summarized_content", "sentiment_reason", mode="before")
    @classmethod
    def check_empty_or_none(cls, v: Any) -> str:
        if v is None:
            return "-"
        s = str(v).strip()
        if not s:
            return "-"
        return s

    @field_validator("impacted_stocks", mode="before")
    @classmethod
    def check_impacted_stocks(cls, v: Any) -> List[str]:
        # 影響銘柄リストがNoneの場合は空リストを返す
        if v is None:
            return []
        if isinstance(v, list):
            return [str(x).strip() for x in v if x is not None]
        return [str(v).strip()]


class NewsSummaryItem(BaseModel):
    """
    元記事とAI要約結果のペアのバリデーションモデル。
    """

    original: NewsItem
    ai_result: AISummaryResult


class FormattedNewsItem(BaseModel):
    """
    最終的に画面に渡す個別ニュース記事のバリデーションモデル。
    """

    title: str = Field(..., description="表示用タイトル")
    original_url: str = Field(default="#", description="元のニュースURL")
    publisher: str = Field(default="-", description="配信元")
    published_at: str = Field(default="", description="配信日時")
    summary: str = Field(..., description="要約コンテンツ")
    sentiment: str = Field(default="neutral", description="センチメント")
    sentiment_reason: str = Field(default="-", description="センチメント理由")
    impacted_stocks: List[str] = Field(
        default_factory=list, description="影響銘柄リスト"
    )

    @field_validator(
        "title",
        "publisher",
        "published_at",
        "summary",
        "sentiment_reason",
        mode="before",
    )
    @classmethod
    def check_empty_or_none(cls, v: Any) -> str:
        if v is None:
            return "-"
        s = str(v).strip()
        if not s:
            return "-"
        return s

    @field_validator("original_url", mode="before")
    @classmethod
    def check_url(cls, v: Any) -> str:
        if v is None:
            return "#"
        s = str(v).strip()
        if not s:
            return "#"
        return s

    @field_validator("sentiment")
    @classmethod
    def validate_sentiment(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in ["positive", "negative", "neutral"]:
            return "neutral"
        return v

    @field_validator("impacted_stocks", mode="before")
    @classmethod
    def check_impacted_stocks(cls, v: Any) -> List[str]:
        if v is None:
            return []
        if isinstance(v, list):
            return [str(x).strip() for x in v if x is not None]
        return [str(v).strip()]


class StockNewsResponse(BaseModel):
    """
    最終レスポンスデータのバリデーションモデル。
    """

    stock_code: str = Field(..., description="銘柄コード")
    items: List[FormattedNewsItem] = Field(
        default_factory=list, description="ニュース一覧"
    )
