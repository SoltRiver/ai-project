"""
ニュース関連銘柄抽出モジュール（ルールベース）
記事のタイトル・本文から上場企業名や証券コードを照合し、
影響銘柄を抽出する。AIに頼らず高速に処理可能。
"""

import re
import logging
from typing import List, Dict, Set, Any

from sqlalchemy.orm import Session
from models.master import StockMaster
from models.news_related_ticker import NewsRelatedTicker

logger = logging.getLogger(__name__)

# 証券コード（4桁）のパターン
_TICKER_PATTERN = re.compile(r"\b(\d{4})\b")


def _load_company_map(db: Session) -> Dict[str, str]:
    """
    stock_masterテーブルから企業名→証券コードのマップを構築する。

    Returns:
        dict: {企業名: 証券コード}
    """
    try:
        masters = db.query(StockMaster.code, StockMaster.name).filter(
            StockMaster.name.isnot(None),
            StockMaster.name != ""
        ).all()
        return {m.name: m.code for m in masters if m.name and m.code}
    except Exception as e:
        logger.warning(f"企業名マップ取得エラー: {e}")
        return {}


def _load_ticker_set(db: Session) -> Set[str]:
    """
    stock_masterテーブルから有効な証券コードのセットを取得する。
    """
    try:
        masters = db.query(StockMaster.code).all()
        return {m.code for m in masters if m.code}
    except Exception as e:
        logger.warning(f"証券コードセット取得エラー: {e}")
        return set()


def extract_tickers_from_text(
    title: str,
    raw_text: str,
    company_map: Dict[str, str],
    valid_tickers: Set[str],
    max_tickers: int = 3
) -> List[Dict[str, Any]]:
    """
    タイトルと本文から関連銘柄を抽出する。

    抽出ロジック:
    1. 企業名辞書で照合（信頼度高）
    2. 4桁数字を証券コードとして照合（タイトルのみ）

    Args:
        title: 記事タイトル
        raw_text: 記事本文
        company_map: {企業名: 証券コード} マップ
        valid_tickers: 有効な証券コードのセット
        max_tickers: 最大抽出件数

    Returns:
        list: [{"ticker_code": "7203", "company_name": "トヨタ自動車", 
                "confidence": 0.8, "extraction_type": "rule"}, ...]
    """
    results = []
    seen_codes = set()
    combined = f"{title} {raw_text}"

    # 1. 企業名辞書で照合
    for company_name, code in company_map.items():
        if len(company_name) < 2:
            continue
        if company_name in combined and code not in seen_codes:
            # タイトルに含まれる場合は信頼度を高くする
            confidence = 0.9 if company_name in title else 0.7
            results.append({
                "ticker_code": code,
                "company_name": company_name,
                "confidence": confidence,
                "extraction_type": "rule",
                "reason": f"記事中に企業名「{company_name}」を検出",
            })
            seen_codes.add(code)

    # 2. 証券コードパターン照合（タイトルのみ — 本文だと年号等と誤検知しやすい）
    for match in _TICKER_PATTERN.finditer(title):
        code = match.group(1)
        if code in valid_tickers and code not in seen_codes:
            # 証券コードで企業名を逆引き
            company_name = "-"
            for name, c in company_map.items():
                if c == code:
                    company_name = name
                    break
            results.append({
                "ticker_code": code,
                "company_name": company_name,
                "confidence": 0.6,
                "extraction_type": "rule",
                "reason": f"タイトルに証券コード「{code}」を検出",
            })
            seen_codes.add(code)

    # 信頼度降順でソートし、上位N件を返す
    results.sort(key=lambda x: -x["confidence"])
    return results[:max_tickers]


def extract_and_save_tickers(
    db: Session,
    article_id: int,
    title: str,
    raw_text: str
) -> List[NewsRelatedTicker]:
    """
    記事から銘柄を抽出し、DBに保存する。
    既存の抽出結果がある場合は削除して再抽出する。

    Args:
        db: DBセッション
        article_id: ニュース記事ID
        title: 記事タイトル
        raw_text: 記事本文

    Returns:
        保存したNewsRelatedTickerオブジェクトのリスト
    """
    # 企業名マップと有効証券コードセットを取得
    company_map = _load_company_map(db)
    valid_tickers = _load_ticker_set(db)

    if not company_map and not valid_tickers:
        logger.warning("企業名マップ・証券コードセットが空のため銘柄抽出をスキップ")
        return []

    # 既存の抽出結果を削除（再抽出のため）
    db.query(NewsRelatedTicker).filter(
        NewsRelatedTicker.news_article_id == article_id,
        NewsRelatedTicker.extraction_type == "rule"
    ).delete()

    # 銘柄抽出
    extracted = extract_tickers_from_text(
        title=title,
        raw_text=raw_text,
        company_map=company_map,
        valid_tickers=valid_tickers
    )

    # DB保存
    saved = []
    for item in extracted:
        ticker = NewsRelatedTicker(
            news_article_id=article_id,
            ticker_code=item["ticker_code"],
            company_name=item["company_name"],
            impact_type="positive",  # ルールベースではデフォルトpositive
            confidence=item["confidence"],
            extraction_type=item["extraction_type"],
            reason=item["reason"],
        )
        db.add(ticker)
        saved.append(ticker)

    logger.info(f"記事ID={article_id}: ルールベースで{len(saved)}件の銘柄を抽出")
    return saved
