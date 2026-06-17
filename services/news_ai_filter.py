"""
ニュースAI対象フィルタモジュール
軽量なルールベースで記事をフィルタリングし、
AI要約の対象を金融・企業関連記事に絞り込む。
"""

import re
import logging
from typing import List, Set

from sqlalchemy.orm import Session
from models.master import StockMaster

logger = logging.getLogger(__name__)


# ================================================================
# 金融・企業関連キーワード
# ================================================================
_FINANCIAL_KEYWORDS_JA = [
    "決算",
    "業績",
    "売上",
    "営業利益",
    "純利益",
    "経常利益",
    "上方修正",
    "下方修正",
    "増収",
    "減収",
    "増益",
    "減益",
    "提携",
    "買収",
    "合併",
    "統合",
    "自社株買い",
    "増配",
    "減配",
    "配当",
    "株式分割",
    "受注",
    "新製品",
    "特許",
    "新薬",
    "行政処分",
    "不正",
    "訴訟",
    "リコール",
    "上場",
    "IPO",
    "上場廃止",
    "MBO",
    "TOB",
    "株価",
    "時価総額",
    "ストップ高",
    "ストップ安",
    "円安",
    "円高",
    "為替",
    "金利",
    "利上げ",
    "利下げ",
    "景気",
    "GDP",
    "CPI",
    "インフレ",
    "デフレ",
    "日経平均",
    "ダウ",
    "S&P",
    "TOPIX",
]

_FINANCIAL_KEYWORDS_EN = [
    "earnings",
    "revenue",
    "profit",
    "loss",
    "guidance",
    "forecast",
    "acquisition",
    "merger",
    "buyback",
    "dividend",
    "IPO",
    "delisting",
    "recall",
    "lawsuit",
    "stock price",
    "market cap",
    "stock split",
    "Fed",
    "BOJ",
    "interest rate",
    "inflation",
    "GDP",
    "CPI",
    "Nikkei",
    "Dow",
]

# 証券コードのパターン（4桁数字）
_TICKER_CODE_PATTERN = re.compile(r"\b\d{4}\b")


def _load_company_names(db: Session) -> Set[str]:
    """
    stock_masterテーブルから上場企業名一覧を取得する。
    キャッシュは呼び出し元で管理する。
    """
    try:
        masters = (
            db.query(StockMaster.name)
            .filter(StockMaster.name.isnot(None), StockMaster.name != "")
            .all()
        )
        return {m.name for m in masters if m.name}
    except Exception as e:
        logger.warning(f"企業名一覧取得エラー: {e}")
        return set()


def is_ai_target(
    title: str, raw_text: str, company_names: Set[str], min_keyword_matches: int = 1
) -> bool:
    """
    記事がAI要約の対象かどうかを判定する。

    判定ロジック:
    1. タイトルまたは本文に金融キーワードが含まれる → 対象
    2. タイトルまたは本文に上場企業名が含まれる → 対象
    3. タイトルまたは本文に証券コードっぽい4桁数字が含まれる → 対象
    4. いずれにも該当しない → 対象外

    Args:
        title: 記事タイトル
        raw_text: 記事本文
        company_names: 上場企業名のセット
        min_keyword_matches: 必要最低キーワードマッチ数

    Returns:
        True: AI対象, False: AI対象外
    """
    combined = f"{title} {raw_text}"

    # 1. 金融キーワードチェック
    keyword_count = 0
    for kw in _FINANCIAL_KEYWORDS_JA:
        if kw in combined:
            keyword_count += 1
    for kw in _FINANCIAL_KEYWORDS_EN:
        if kw.lower() in combined.lower():
            keyword_count += 1

    if keyword_count >= min_keyword_matches:
        return True

    # 2. 上場企業名チェック
    for name in company_names:
        if len(name) >= 2 and name in combined:
            return True

    # 3. 証券コードチェック（タイトルのみ。本文だと誤検知が多いため）
    if _TICKER_CODE_PATTERN.search(title):
        return True

    return False


def filter_articles_for_ai(db: Session, articles: list) -> list:
    """
    記事リストに対してAI対象フィルタを適用し、
    各記事の is_ai_target フラグと ai_status を設定する。

    Args:
        db: DBセッション
        articles: NewsArticle オブジェクトのリスト

    Returns:
        更新された記事リスト
    """
    # 企業名一覧を一度だけ取得
    company_names = _load_company_names(db)
    logger.info(f"企業名辞書: {len(company_names)} 件ロード")

    ai_target_count = 0
    skipped_count = 0

    for article in articles:
        # 既にステータスが確定している記事はスキップ
        if article.ai_status in ("summarized", "processing", "queued"):
            continue

        target = is_ai_target(
            title=article.title or "",
            raw_text=article.raw_text or "",
            company_names=company_names,
        )

        article.is_ai_target = target
        if target:
            article.ai_status = "queued"
            ai_target_count += 1
        else:
            article.ai_status = "skipped"
            skipped_count += 1

    logger.info(
        f"AI対象フィルタ結果: 対象={ai_target_count}件, スキップ={skipped_count}件"
    )
    return articles
