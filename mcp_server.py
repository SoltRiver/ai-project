"""
EDINET DB MCPサーバー

EDINET DBに蓄積された銘柄情報をMCPプロトコル経由で
AIエージェント（Claude Desktop, Cursor 等）から取得可能にする。

データ取得優先順位:
  1. EDINET DB（ローカルDB内のキャッシュ・蓄積データ）
  2. 既存の取得処理（yfinance, j-Quants等）へのフォールバック

使用方法:
  python mcp_server.py
  （stdio トランスポートで起動し、MCP クライアントから接続）
"""

import os
import sys
import json
import logging
from datetime import datetime, date
from typing import Optional, Any
from decimal import Decimal

# .env ファイルから環境変数を読み込む
from dotenv import load_dotenv

load_dotenv()

from mcp.server.fastmcp import FastMCP

# プロジェクトルートをパスに追加（モジュール解決用）
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# DB接続
from database import SessionLocal
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, desc

# EDINETモデル群
from models.edinet_document import EdinetDocument
from models.edinet_xbrl_fact import EdinetXbrlFact
from models.edinet_financial_highlight import EdinetFinancialHighlight
from models.edinet_facts_snapshot import EdinetFactsSnapshot
from models.edinet_diff_summary import EdinetDiffSummary
from models.edinet_derived import EdinetFinancialDerived
from models.edinet_timeseries import EdinetMetricTimeseries, EdinetMetricComparison
from models.edinet_ai_summary import EdinetAISummary
from models.company_info import CompanyInfo
from models.master import StockMaster

# ロガー設定
logger = logging.getLogger("mcp_server")
logger.setLevel(logging.INFO)

# =====================================================
# ヘルパー関数
# =====================================================

# 欠損値の代替表記（ユーザールール準拠: None → "-"）
MISSING = "-"


def _safe_str(val: Any) -> str:
    """値を安全に文字列化する。None や空値は "-" を返す"""
    if val is None:
        return MISSING
    if isinstance(val, Decimal):
        return str(float(val))
    if isinstance(val, (date, datetime)):
        return val.isoformat()
    return str(val)


def _get_db() -> Session:
    """DBセッションを取得する"""
    return SessionLocal()


def _sec_code_from_stock_code(stock_code: str) -> str:
    """
    4桁の銘柄コードを5桁のsec_code形式に変換する。
    EDINET DBでは sec_code = 4桁 + '0' の形式で保存されている。
    """
    code = stock_code.replace(".T", "").strip()
    if len(code) == 4 and code.isdigit():
        return code + "0"
    return code


def _format_large_number(val: Any) -> str:
    """大きな数値を読みやすい形式にフォーマットする（百万円単位等）"""
    if val is None:
        return MISSING
    try:
        num = float(val)
    except (ValueError, TypeError):
        return _safe_str(val)

    abs_num = abs(num)
    if abs_num >= 1e12:
        return f"{num / 1e12:.2f}兆円"
    elif abs_num >= 1e8:
        return f"{num / 1e8:.2f}億円"
    elif abs_num >= 1e4:
        return f"{num / 1e4:.2f}万円"
    else:
        return f"{num:,.0f}円"


# =====================================================
# MCPサーバー初期化
# =====================================================

mcp = FastMCP(
    "EDINET DB Server",
)


# =====================================================
# Tool 1: 企業検索
# =====================================================


@mcp.tool()
def search_company(query: str) -> str:
    """
    銘柄コードまたは企業名でEDINET DB内の企業情報を検索する。

    優先順位:
      1. EDINET DB（edinet_documents / company_info / stock_master）
      2. yfinance フォールバック

    Args:
        query: 銘柄コード（例: "7203"）または企業名の一部（例: "トヨタ"）

    Returns:
        マッチした企業情報のJSON文字列
    """
    db = _get_db()
    try:
        results = []

        # --- Phase 1: EDINET DB から検索 ---

        # 1a. stock_master からの検索
        master_query = db.query(StockMaster)
        if query.isdigit():
            master_query = master_query.filter(StockMaster.code == query)
        else:
            master_query = master_query.filter(StockMaster.name.contains(query))
        masters = master_query.limit(20).all()

        for m in masters:
            # company_info との結合を試みる
            company = (
                db.query(CompanyInfo).filter(CompanyInfo.stock_code == m.code).first()
            )

            entry = {
                "stock_code": m.code,
                "name": _safe_str(m.name),
                "market": _safe_str(m.market),
            }

            if company:
                entry.update(
                    {
                        "edinet_code": _safe_str(company.edinet_code),
                        "corporate_name_ja": _safe_str(company.corporate_name_ja),
                        "address": _safe_str(company.address),
                        "capital": _format_large_number(company.capital),
                        "representative": _safe_str(company.representative),
                        "settlement_date": _safe_str(company.settlement_date),
                    }
                )

            # 最新の提出書類情報を付与
            sec_code = _sec_code_from_stock_code(m.code)
            latest_doc = (
                db.query(EdinetDocument)
                .filter(
                    EdinetDocument.sec_code == sec_code,
                    EdinetDocument.doc_type_code == "120",  # 有価証券報告書
                )
                .order_by(desc(EdinetDocument.submit_datetime))
                .first()
            )

            if latest_doc:
                entry["latest_annual_report"] = {
                    "doc_id": latest_doc.doc_id,
                    "period": f"{_safe_str(latest_doc.period_start)} ～ {_safe_str(latest_doc.period_end)}",
                    "submit_date": _safe_str(latest_doc.submit_datetime),
                    "filer_name": _safe_str(latest_doc.filer_name),
                }

            results.append(entry)

        # 1b. edinet_documents の filer_name からも検索
        if not results and not query.isdigit():
            docs = (
                db.query(EdinetDocument)
                .filter(EdinetDocument.filer_name.contains(query))
                .group_by(EdinetDocument.edinet_code)
                .limit(10)
                .all()
            )

            for doc in docs:
                results.append(
                    {
                        "edinet_code": _safe_str(doc.edinet_code),
                        "sec_code": _safe_str(doc.sec_code),
                        "filer_name": _safe_str(doc.filer_name),
                        "latest_doc_id": doc.doc_id,
                        "doc_description": _safe_str(doc.doc_description),
                    }
                )

        # --- Phase 2: yfinance フォールバック ---
        if not results and query.isdigit():
            try:
                from services.data_fetcher import (
                    fetch_stock_info,
                    format_symbol_for_yfinance,
                )

                symbol = format_symbol_for_yfinance(query)
                info = fetch_stock_info(symbol)
                if info:
                    results.append(
                        {
                            "stock_code": query,
                            "name": _safe_str(info.get("name")),
                            "current_price": _safe_str(info.get("current_price")),
                            "market_cap": _format_large_number(info.get("market_cap")),
                            "sector": _safe_str(info.get("sector")),
                            "industry": _safe_str(info.get("industry")),
                            "source": "yfinance（EDINET DB に該当データなし）",
                        }
                    )
            except Exception as e:
                logger.warning(f"yfinance フォールバック失敗: {e}")

        if not results:
            return json.dumps(
                {"message": f"「{query}」に該当する企業は見つかりませんでした。"},
                ensure_ascii=False,
            )

        return json.dumps(
            {"count": len(results), "companies": results}, ensure_ascii=False, indent=2
        )

    finally:
        db.close()


# =====================================================
# Tool 2: 提出書類一覧
# =====================================================


@mcp.tool()
def get_company_filings(
    stock_code: str, doc_type: Optional[str] = None, limit: int = 10
) -> str:
    """
    指定銘柄の EDINET 提出書類一覧を取得する。

    Args:
        stock_code: 銘柄コード（例: "7203"）
        doc_type: 書類種別コード（省略時は全種別）。例: "120"=有価証券報告書, "140"=四半期報告書
        limit: 取得件数（デフォルト10件）

    Returns:
        書類一覧のJSON文字列
    """
    db = _get_db()
    try:
        sec_code = _sec_code_from_stock_code(stock_code)

        query = db.query(EdinetDocument).filter(EdinetDocument.sec_code == sec_code)

        if doc_type:
            query = query.filter(EdinetDocument.doc_type_code == doc_type)

        docs = query.order_by(desc(EdinetDocument.submit_datetime)).limit(limit).all()

        if not docs:
            return json.dumps(
                {
                    "message": f"銘柄コード {stock_code} の書類が見つかりませんでした。",
                    "hint": "EDINET DBにデータが蓄積されていない場合があります。",
                },
                ensure_ascii=False,
            )

        filings = []
        for doc in docs:
            filings.append(
                {
                    "doc_id": doc.doc_id,
                    "doc_type_code": _safe_str(doc.doc_type_code),
                    "doc_description": _safe_str(doc.doc_description),
                    "filer_name": _safe_str(doc.filer_name),
                    "edinet_code": _safe_str(doc.edinet_code),
                    "period_start": _safe_str(doc.period_start),
                    "period_end": _safe_str(doc.period_end),
                    "submit_datetime": _safe_str(doc.submit_datetime),
                    "xbrl_flag": _safe_str(doc.xbrl_flag),
                    "pdf_flag": _safe_str(doc.pdf_flag),
                }
            )

        return json.dumps(
            {"stock_code": stock_code, "count": len(filings), "filings": filings},
            ensure_ascii=False,
            indent=2,
        )

    finally:
        db.close()


# =====================================================
# Tool 3: 財務ハイライト
# =====================================================


@mcp.tool()
def get_financial_highlights(doc_id: str) -> str:
    """
    指定書類の財務ハイライト（主要指標）を取得する。

    優先順位:
      1. EDINET DB（edinet_financial_highlight テーブル）
      2. XBRL ファクトからの直接抽出
      3. yfinance フォールバック（銘柄コード判明時）

    Args:
        doc_id: EDINET 書類ID（例: "S100TR7I"）

    Returns:
        財務指標のJSON文字列
    """
    db = _get_db()
    try:
        # --- Phase 1: edinet_financial_highlight から取得 ---
        highlights = (
            db.query(EdinetFinancialHighlight)
            .filter(EdinetFinancialHighlight.doc_id == doc_id)
            .all()
        )

        if highlights:
            metrics = {}
            for hl in highlights:
                metrics[hl.metric_key] = {
                    "label": _safe_str(hl.metric_label),
                    "value": _safe_str(hl.value_numeric),
                    "value_formatted": _format_large_number(hl.value_numeric),
                    "unit": _safe_str(hl.unit_label),
                    "scope": _safe_str(hl.scope),
                    "period_type": _safe_str(hl.period_type),
                    "period_start": _safe_str(hl.period_start),
                    "period_end": _safe_str(hl.period_end),
                    "confidence": _safe_str(hl.confidence),
                    "source_concept": _safe_str(hl.source_concept),
                }

            # 書類メタデータも付与
            doc = (
                db.query(EdinetDocument).filter(EdinetDocument.doc_id == doc_id).first()
            )
            result = {
                "doc_id": doc_id,
                "source": "EDINET DB (financial_highlight)",
                "filer_name": _safe_str(doc.filer_name) if doc else MISSING,
                "period": (
                    f"{_safe_str(doc.period_start)} ～ {_safe_str(doc.period_end)}"
                    if doc
                    else MISSING
                ),
                "metrics_count": len(metrics),
                "metrics": metrics,
            }
            return json.dumps(result, ensure_ascii=False, indent=2)

        # --- Phase 2: edinet_facts_snapshot から取得 ---
        snapshots = (
            db.query(EdinetFactsSnapshot)
            .filter(EdinetFactsSnapshot.doc_id == doc_id)
            .all()
        )

        if snapshots:
            metrics = {}
            for snap in snapshots:
                metrics[snap.metric_key] = {
                    "value": _safe_str(snap.value),
                    "value_formatted": _format_large_number(snap.value),
                    "unit": _safe_str(snap.unit),
                    "scope": _safe_str(snap.consolidation_scope),
                    "source_locator": _safe_str(snap.source_locator),
                }

            doc = (
                db.query(EdinetDocument).filter(EdinetDocument.doc_id == doc_id).first()
            )
            result = {
                "doc_id": doc_id,
                "source": "EDINET DB (facts_snapshot)",
                "filer_name": _safe_str(doc.filer_name) if doc else MISSING,
                "metrics_count": len(metrics),
                "metrics": metrics,
            }
            return json.dumps(result, ensure_ascii=False, indent=2)

        # --- Phase 3: yfinance フォールバック ---
        doc = db.query(EdinetDocument).filter(EdinetDocument.doc_id == doc_id).first()
        if doc and doc.sec_code:
            stock_code = doc.sec_code[:4] if doc.sec_code else None
            if stock_code:
                try:
                    from services.data_fetcher import (
                        fetch_stock_info,
                        format_symbol_for_yfinance,
                    )

                    symbol = format_symbol_for_yfinance(stock_code)
                    info = fetch_stock_info(symbol)
                    if info:
                        result = {
                            "doc_id": doc_id,
                            "source": "yfinance（EDINET DB に財務データなし）",
                            "filer_name": _safe_str(doc.filer_name),
                            "note": "EDINET DB にハイライトデータが未登録のため、yfinance からリアルタイムデータを取得しました",
                            "metrics": {
                                "revenue": {
                                    "value_formatted": _format_large_number(
                                        info.get("total_revenue")
                                    ),
                                    "label": "売上高",
                                },
                                "net_income": {
                                    "value_formatted": _format_large_number(
                                        info.get("net_income")
                                    ),
                                    "label": "当期純利益",
                                },
                                "operating_margins": {
                                    "value": _safe_str(info.get("operating_margins")),
                                    "label": "営業利益率",
                                },
                                "return_on_equity": {
                                    "value": _safe_str(info.get("return_on_equity")),
                                    "label": "ROE",
                                },
                                "return_on_assets": {
                                    "value": _safe_str(info.get("return_on_assets")),
                                    "label": "ROA",
                                },
                                "market_cap": {
                                    "value_formatted": _format_large_number(
                                        info.get("market_cap")
                                    ),
                                    "label": "時価総額",
                                },
                            },
                        }
                        return json.dumps(result, ensure_ascii=False, indent=2)
                except Exception as e:
                    logger.warning(f"yfinance フォールバック失敗: {e}")

        return json.dumps(
            {"doc_id": doc_id, "message": "該当する財務データが見つかりませんでした。"},
            ensure_ascii=False,
        )

    finally:
        db.close()


# =====================================================
# Tool 4: 前年度比較差分
# =====================================================


@mcp.tool()
def get_financial_diff(doc_id: str, force_regenerate: bool = False) -> str:
    """
    指定書類の前年度との差分比較を取得する（固定6指標 + 変化大3件）。

    優先順位:
      1. EDINET DB キャッシュ（edinet_diff_summary テーブル）
      2. 動的生成（edinet_diff_service の generate_diff_summary）

    Args:
        doc_id: EDINET 書類ID（例: "S100TR7I"）
        force_regenerate: True の場合、キャッシュを無視して再生成する

    Returns:
        差分比較データのJSON文字列
    """
    db = _get_db()
    try:
        # --- Phase 1: キャッシュ済みの差分を検索 ---
        if not force_regenerate:
            cached = (
                db.query(EdinetDiffSummary)
                .filter(EdinetDiffSummary.current_doc_id == doc_id)
                .first()
            )

            if cached and cached.json_payload:
                result = (
                    cached.json_payload.copy()
                    if isinstance(cached.json_payload, dict)
                    else {}
                )
                result["status"] = _safe_str(cached.status)
                result["notes"] = _safe_str(cached.notes)
                result["generated_at"] = _safe_str(cached.generated_at)
                result["source"] = "EDINET DB (diff_summary キャッシュ)"
                return json.dumps(result, ensure_ascii=False, indent=2, default=str)

        # --- Phase 2: 動的生成を試みる ---
        try:
            from services.edinet_diff_service import get_or_generate_diff

            diff_data = get_or_generate_diff(db, doc_id, force=force_regenerate)
            diff_data["source"] = "EDINET DB (動的生成)"
            return json.dumps(diff_data, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logger.error(f"差分生成失敗: {e}")
            return json.dumps(
                {
                    "doc_id": doc_id,
                    "status": "failed",
                    "message": f"差分生成に失敗しました: {str(e)}",
                },
                ensure_ascii=False,
            )

    finally:
        db.close()


# =====================================================
# Tool 5: 時系列データ
# =====================================================


@mcp.tool()
def get_financial_timeseries(stock_code: str, metric_key: Optional[str] = None) -> str:
    """
    指定銘柄の財務指標時系列データを取得する。

    優先順位:
      1. EDINET DB（edinet_metric_timeseries テーブル）
      2. edinet_metric_comparison テーブル（YoY, CAGR含む）

    Args:
        stock_code: 銘柄コード（例: "7203"）
        metric_key: 指標キー（省略時は全指標）。例: "revenue", "operating_profit", "net_income"

    Returns:
        時系列データのJSON文字列
    """
    db = _get_db()
    try:
        sec_code = _sec_code_from_stock_code(stock_code)

        # --- 時系列データ取得 ---
        ts_query = db.query(EdinetMetricTimeseries).filter(
            EdinetMetricTimeseries.sec_code == sec_code
        )
        if metric_key:
            ts_query = ts_query.filter(EdinetMetricTimeseries.metric_key == metric_key)

        ts_data = ts_query.order_by(
            EdinetMetricTimeseries.metric_key, EdinetMetricTimeseries.period_end_year
        ).all()

        # --- 比較データ取得 ---
        comp_query = db.query(EdinetMetricComparison).filter(
            EdinetMetricComparison.sec_code == sec_code
        )
        if metric_key:
            comp_query = comp_query.filter(
                EdinetMetricComparison.metric_key == metric_key
            )

        comp_data = comp_query.order_by(
            EdinetMetricComparison.metric_key, EdinetMetricComparison.period_end_year
        ).all()

        if not ts_data and not comp_data:
            return json.dumps(
                {
                    "stock_code": stock_code,
                    "message": "時系列データが見つかりませんでした。EDINET DB にデータが蓄積されていない可能性があります。",
                },
                ensure_ascii=False,
            )

        # 時系列データの整形
        timeseries = {}
        for ts in ts_data:
            key = ts.metric_key
            if key not in timeseries:
                timeseries[key] = []
            timeseries[key].append(
                {
                    "year": ts.period_end_year,
                    "fiscal_year": _safe_str(ts.fiscal_year_label),
                    "value": _safe_str(ts.value_numeric),
                    "value_formatted": _format_large_number(ts.value_numeric),
                    "doc_id": _safe_str(ts.doc_id),
                }
            )

        # 比較データの整形
        comparisons = {}
        for comp in comp_data:
            key = comp.metric_key
            if key not in comparisons:
                comparisons[key] = []
            comparisons[key].append(
                {
                    "year": comp.period_end_year,
                    "yoy_abs": _safe_str(comp.yoy_abs),
                    "yoy_pct": _safe_str(comp.yoy_pct),
                    "cagr_3y": _safe_str(comp.cagr_3y),
                    "cagr_5y": _safe_str(comp.cagr_5y),
                    "trend_label": _safe_str(comp.trend_label),
                    "trend_reason": _safe_str(comp.trend_reason),
                    "turnaround_flag": _safe_str(comp.turnaround_flag),
                }
            )

        result = {
            "stock_code": stock_code,
            "source": "EDINET DB (timeseries)",
            "timeseries": timeseries,
            "comparisons": comparisons,
        }
        return json.dumps(result, ensure_ascii=False, indent=2, default=str)

    finally:
        db.close()


# =====================================================
# Tool 6: XBRLファクト検索
# =====================================================


@mcp.tool()
def get_xbrl_facts(doc_id: str, concept: Optional[str] = None, limit: int = 50) -> str:
    """
    指定書類のXBRLファクトデータ（生データ）を取得する。

    Args:
        doc_id: EDINET 書類ID（例: "S100TR7I"）
        concept: XBRLコンセプト名でフィルタ（省略時は主要項目のみ）。例: "jppfs_cor:NetSales"
        limit: 取得件数上限（デフォルト50）

    Returns:
        XBRLファクトのJSON文字列
    """
    db = _get_db()
    try:
        query = db.query(EdinetXbrlFact).filter(EdinetXbrlFact.doc_id == doc_id)

        if concept:
            # 部分一致検索を許可（例: "NetSales" → "jppfs_cor:NetSales" にマッチ）
            query = query.filter(EdinetXbrlFact.concept.contains(concept))

        facts = query.order_by(EdinetXbrlFact.concept).limit(limit).all()

        if not facts:
            return json.dumps(
                {"doc_id": doc_id, "message": "XBRLファクトが見つかりませんでした。"},
                ensure_ascii=False,
            )

        fact_list = []
        for f in facts:
            fact_list.append(
                {
                    "concept": _safe_str(f.concept),
                    "value_text": _safe_str(f.value_text),
                    "value_numeric": _safe_str(f.value_numeric),
                    "unit_ref": _safe_str(f.unit_ref),
                    "decimals": _safe_str(f.decimals),
                    "context_ref": _safe_str(f.context_ref),
                    "period_start": _safe_str(f.period_start),
                    "period_end": _safe_str(f.period_end),
                    "instant_date": _safe_str(f.instant_date),
                }
            )

        # 書類メタデータも付与
        doc = db.query(EdinetDocument).filter(EdinetDocument.doc_id == doc_id).first()

        return json.dumps(
            {
                "doc_id": doc_id,
                "filer_name": _safe_str(doc.filer_name) if doc else MISSING,
                "source": "EDINET DB (xbrl_fact)",
                "count": len(fact_list),
                "facts": fact_list,
            },
            ensure_ascii=False,
            indent=2,
        )

    finally:
        db.close()


# =====================================================
# Tool 7: 派生指標
# =====================================================


@mcp.tool()
def get_derived_metrics(doc_id: str) -> str:
    """
    指定書類の派生指標（ROE、自己資本比率等）を取得する。

    優先順位:
      1. EDINET DB（edinet_financial_derived テーブル）
      2. facts_snapshot からの動的計算
      3. yfinance フォールバック

    Args:
        doc_id: EDINET 書類ID（例: "S100TR7I"）

    Returns:
        派生指標のJSON文字列
    """
    db = _get_db()
    try:
        # --- Phase 1: edinet_financial_derived から取得 ---
        derived = (
            db.query(EdinetFinancialDerived)
            .filter(EdinetFinancialDerived.doc_id == doc_id)
            .all()
        )

        if derived:
            metrics = {}
            for d in derived:
                metrics[d.derived_key] = {
                    "label": _safe_str(d.derived_label),
                    "value": _safe_str(d.value_numeric),
                    "formula": _safe_str(d.calculation_formula),
                    "source_metrics": d.source_metrics,
                    "source_values": d.source_values,
                    "confidence": _safe_str(d.confidence),
                    "reason": _safe_str(d.reason),
                }

            doc = (
                db.query(EdinetDocument).filter(EdinetDocument.doc_id == doc_id).first()
            )
            return json.dumps(
                {
                    "doc_id": doc_id,
                    "source": "EDINET DB (financial_derived)",
                    "filer_name": _safe_str(doc.filer_name) if doc else MISSING,
                    "metrics_count": len(metrics),
                    "metrics": metrics,
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            )

        # --- Phase 2: facts_snapshot から動的計算を試みる ---
        snapshots = (
            db.query(EdinetFactsSnapshot)
            .filter(EdinetFactsSnapshot.doc_id == doc_id)
            .all()
        )

        if snapshots:
            snap_map = {s.metric_key: s.value for s in snapshots}
            calculated = {}

            # 自己資本比率の計算
            equity = snap_map.get("equity")
            total_assets = snap_map.get("total_assets")
            if equity is not None and total_assets is not None and total_assets != 0:
                ratio = float(Decimal(str(equity)) / Decimal(str(total_assets)))
                calculated["equity_ratio"] = {
                    "label": "自己資本比率",
                    "value": f"{ratio:.4f}",
                    "value_pct": f"{ratio * 100:.2f}%",
                    "formula": "equity / total_assets",
                }

            # 営業利益率の計算
            op_profit = snap_map.get("operating_profit")
            revenue = snap_map.get("revenue")
            if op_profit is not None and revenue is not None and revenue != 0:
                margin = float(Decimal(str(op_profit)) / Decimal(str(revenue)))
                calculated["operating_margin"] = {
                    "label": "営業利益率",
                    "value": f"{margin:.4f}",
                    "value_pct": f"{margin * 100:.2f}%",
                    "formula": "operating_profit / revenue",
                }

            if calculated:
                doc = (
                    db.query(EdinetDocument)
                    .filter(EdinetDocument.doc_id == doc_id)
                    .first()
                )
                return json.dumps(
                    {
                        "doc_id": doc_id,
                        "source": "EDINET DB (facts_snapshot から動的計算)",
                        "filer_name": _safe_str(doc.filer_name) if doc else MISSING,
                        "metrics": calculated,
                    },
                    ensure_ascii=False,
                    indent=2,
                )

        # --- Phase 3: yfinance フォールバック ---
        doc = db.query(EdinetDocument).filter(EdinetDocument.doc_id == doc_id).first()
        if doc and doc.sec_code:
            stock_code = doc.sec_code[:4]
            try:
                from services.fundamental_fetcher import fetch_fundamental_data

                fund_data = fetch_fundamental_data(stock_code)
                if fund_data:
                    return json.dumps(
                        {
                            "doc_id": doc_id,
                            "source": "yfinance（EDINET DB に派生データなし）",
                            "filer_name": _safe_str(doc.filer_name),
                            "metrics": {
                                "roe": {
                                    "label": "ROE",
                                    "value": _safe_str(
                                        fund_data.get("return_on_equity")
                                    ),
                                },
                                "roa": {
                                    "label": "ROA",
                                    "value": _safe_str(
                                        fund_data.get("return_on_assets")
                                    ),
                                },
                                "per": {
                                    "label": "PER",
                                    "value": _safe_str(fund_data.get("per")),
                                },
                                "pbr": {
                                    "label": "PBR",
                                    "value": _safe_str(fund_data.get("pbr")),
                                },
                                "operating_margin": {
                                    "label": "営業利益率",
                                    "value": _safe_str(
                                        fund_data.get("operating_margin")
                                    ),
                                },
                                "profit_margin": {
                                    "label": "利益率",
                                    "value": _safe_str(fund_data.get("profit_margin")),
                                },
                            },
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
            except Exception as e:
                logger.warning(f"yfinance フォールバック失敗: {e}")

        return json.dumps(
            {"doc_id": doc_id, "message": "派生指標データが見つかりませんでした。"},
            ensure_ascii=False,
        )

    finally:
        db.close()


# =====================================================
# Tool 8: 日次書類一覧
# =====================================================


@mcp.tool()
def get_documents_by_date(
    target_date: str, doc_type: Optional[str] = None, limit: int = 50
) -> str:
    """
    指定日に提出された EDINET 書類一覧を取得する。

    優先順位:
      1. EDINET DB（edinet_documents テーブル）
      2. EDINET API 直接呼び出し（DB にデータなしの場合）

    Args:
        target_date: 対象日（YYYY-MM-DD 形式）。例: "2024-06-25"
        doc_type: 書類種別コードでフィルタ（省略時は全種別）。例: "120"=有報, "140"=四半期
        limit: 取得件数上限（デフォルト50）

    Returns:
        書類一覧のJSON文字列
    """
    db = _get_db()
    try:
        # 日付パース
        try:
            parsed_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        except ValueError:
            return json.dumps(
                {
                    "error": f"日付形式が不正です: {target_date}。YYYY-MM-DD 形式で指定してください。"
                },
                ensure_ascii=False,
            )

        # --- Phase 1: EDINET DB から検索 ---
        query = db.query(EdinetDocument).filter(
            EdinetDocument.target_date == parsed_date
        )
        if doc_type:
            query = query.filter(EdinetDocument.doc_type_code == doc_type)

        docs = query.order_by(desc(EdinetDocument.submit_datetime)).limit(limit).all()

        if docs:
            doc_list = []
            for doc in docs:
                doc_list.append(
                    {
                        "doc_id": doc.doc_id,
                        "doc_type_code": _safe_str(doc.doc_type_code),
                        "doc_description": _safe_str(doc.doc_description),
                        "filer_name": _safe_str(doc.filer_name),
                        "edinet_code": _safe_str(doc.edinet_code),
                        "sec_code": _safe_str(doc.sec_code),
                        "period_start": _safe_str(doc.period_start),
                        "period_end": _safe_str(doc.period_end),
                        "submit_datetime": _safe_str(doc.submit_datetime),
                    }
                )

            return json.dumps(
                {
                    "target_date": target_date,
                    "source": "EDINET DB",
                    "count": len(doc_list),
                    "documents": doc_list,
                },
                ensure_ascii=False,
                indent=2,
            )

        # --- Phase 2: EDINET API 直接呼び出し ---
        try:
            from services.edinet_service import EdinetClient as LegacyEdinetClient

            client = LegacyEdinetClient()
            api_docs = client.get_documents_by_date(parsed_date, type_code=2)

            if api_docs:
                doc_list = []
                for api_doc in api_docs[:limit]:
                    doc_list.append(
                        {
                            "doc_id": _safe_str(api_doc.get("docID")),
                            "doc_type_code": _safe_str(api_doc.get("docTypeCode")),
                            "doc_description": _safe_str(api_doc.get("docDescription")),
                            "filer_name": _safe_str(api_doc.get("filerName")),
                            "edinet_code": _safe_str(api_doc.get("edinetCode")),
                            "sec_code": _safe_str(api_doc.get("secCode")),
                            "period_start": _safe_str(api_doc.get("periodStart")),
                            "period_end": _safe_str(api_doc.get("periodEnd")),
                            "submit_datetime": _safe_str(api_doc.get("submitDateTime")),
                        }
                    )

                return json.dumps(
                    {
                        "target_date": target_date,
                        "source": "EDINET API（DB にデータなし、リアルタイム取得）",
                        "count": len(doc_list),
                        "documents": doc_list,
                    },
                    ensure_ascii=False,
                    indent=2,
                )

        except Exception as e:
            logger.warning(f"EDINET API フォールバック失敗: {e}")

        return json.dumps(
            {
                "target_date": target_date,
                "message": "指定日の書類が見つかりませんでした。",
            },
            ensure_ascii=False,
        )

    finally:
        db.close()


# =====================================================
# 追加ツール: AI要約取得
# =====================================================


@mcp.tool()
def get_ai_summary(stock_code: str, year: Optional[int] = None) -> str:
    """
    指定銘柄のAI生成要約（SNAPSHOT/DELTA）を取得する。

    Args:
        stock_code: 銘柄コード（例: "7203"）
        year: 対象年度（省略時は最新）

    Returns:
        AI要約のJSON文字列
    """
    db = _get_db()
    try:
        sec_code = _sec_code_from_stock_code(stock_code)

        query = db.query(EdinetAISummary).filter(EdinetAISummary.sec_code == sec_code)
        if year:
            query = query.filter(EdinetAISummary.period_end_year == year)

        summaries = query.order_by(
            desc(EdinetAISummary.period_end_year), EdinetAISummary.kind
        ).all()

        if not summaries:
            return json.dumps(
                {
                    "stock_code": stock_code,
                    "message": "AI要約データが見つかりませんでした。",
                },
                ensure_ascii=False,
            )

        summary_list = []
        for s in summaries:
            summary_list.append(
                {
                    "year": s.period_end_year,
                    "kind": _safe_str(s.kind),
                    "summary_text": _safe_str(s.summary_text),
                    "bullet_points": s.bullet_points,
                    "created_at": _safe_str(s.created_at),
                }
            )

        return json.dumps(
            {
                "stock_code": stock_code,
                "source": "EDINET DB (ai_summary)",
                "count": len(summary_list),
                "summaries": summary_list,
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    finally:
        db.close()


# =====================================================
# 追加ツール: 銘柄総合情報
# =====================================================


@mcp.tool()
def get_stock_overview(stock_code: str) -> str:
    """
    銘柄の総合情報を一括取得する（企業情報 + 最新財務 + 派生指標）。
    複数ソースを自動で統合し、EDINET DB を優先する。

    Args:
        stock_code: 銘柄コード（例: "7203"）

    Returns:
        総合情報のJSON文字列
    """
    db = _get_db()
    try:
        sec_code = _sec_code_from_stock_code(stock_code)
        overview = {
            "stock_code": stock_code,
            "sources_used": [],
        }

        # --- 1. 企業基本情報 ---
        master = db.query(StockMaster).filter(StockMaster.code == stock_code).first()
        if master:
            overview["company"] = {
                "name": _safe_str(master.name),
                "market": _safe_str(master.market),
            }
            overview["sources_used"].append("stock_master")

        company = (
            db.query(CompanyInfo).filter(CompanyInfo.stock_code == stock_code).first()
        )
        if company:
            overview.setdefault("company", {}).update(
                {
                    "edinet_code": _safe_str(company.edinet_code),
                    "corporate_name_ja": _safe_str(company.corporate_name_ja),
                    "capital": _format_large_number(company.capital),
                    "representative": _safe_str(company.representative),
                    "settlement_date": _safe_str(company.settlement_date),
                }
            )
            overview["sources_used"].append("company_info")

        # --- 2. 最新の有報情報 ---
        latest_doc = (
            db.query(EdinetDocument)
            .filter(
                EdinetDocument.sec_code == sec_code,
                EdinetDocument.doc_type_code == "120",
            )
            .order_by(desc(EdinetDocument.submit_datetime))
            .first()
        )

        if latest_doc:
            overview["latest_annual_report"] = {
                "doc_id": latest_doc.doc_id,
                "filer_name": _safe_str(latest_doc.filer_name),
                "period": f"{_safe_str(latest_doc.period_start)} ～ {_safe_str(latest_doc.period_end)}",
                "submit_date": _safe_str(latest_doc.submit_datetime),
            }
            overview["sources_used"].append("edinet_documents")

            # 財務ハイライト
            highlights = (
                db.query(EdinetFinancialHighlight)
                .filter(EdinetFinancialHighlight.doc_id == latest_doc.doc_id)
                .all()
            )

            if highlights:
                overview["financial_highlights"] = {}
                for hl in highlights:
                    overview["financial_highlights"][hl.metric_key] = {
                        "label": _safe_str(hl.metric_label),
                        "value_formatted": _format_large_number(hl.value_numeric),
                        "scope": _safe_str(hl.scope),
                    }
                overview["sources_used"].append("financial_highlight")

            # 派生指標
            derived = (
                db.query(EdinetFinancialDerived)
                .filter(EdinetFinancialDerived.doc_id == latest_doc.doc_id)
                .all()
            )

            if derived:
                overview["derived_metrics"] = {}
                for d in derived:
                    overview["derived_metrics"][d.derived_key] = {
                        "label": _safe_str(d.derived_label),
                        "value": _safe_str(d.value_numeric),
                        "confidence": _safe_str(d.confidence),
                    }
                overview["sources_used"].append("financial_derived")

            # 差分サマリー
            diff = (
                db.query(EdinetDiffSummary)
                .filter(EdinetDiffSummary.current_doc_id == latest_doc.doc_id)
                .first()
            )

            if diff and diff.json_payload:
                fixed_six = diff.json_payload.get("fixed_six", [])
                overview["yoy_diff"] = {
                    "status": _safe_str(diff.status),
                    "prev_doc_id": _safe_str(diff.prev_doc_id),
                    "fixed_six_summary": [
                        {
                            "metric": item.get(
                                "metric_label", item.get("metric_key", MISSING)
                            ),
                            "current": item.get("current_value", MISSING),
                            "prev": item.get("prev_value", MISSING),
                            "delta_pct": (
                                f"{item['delta_pct']:.1%}"
                                if item.get("delta_pct") is not None
                                else MISSING
                            ),
                        }
                        for item in fixed_six
                    ],
                }
                overview["sources_used"].append("diff_summary")

        # --- 3. yfinance フォールバック（EDINET DB に十分なデータがない場合） ---
        if "financial_highlights" not in overview:
            try:
                from services.data_fetcher import (
                    fetch_stock_info,
                    format_symbol_for_yfinance,
                )

                symbol = format_symbol_for_yfinance(stock_code)
                info = fetch_stock_info(symbol)
                if info:
                    overview["market_data"] = {
                        "current_price": _safe_str(info.get("current_price")),
                        "change": _safe_str(info.get("change")),
                        "change_percent": (
                            f"{info['change_percent']:.2f}%"
                            if info.get("change_percent")
                            else MISSING
                        ),
                        "market_cap": _format_large_number(info.get("market_cap")),
                        "volume": _safe_str(info.get("volume")),
                        "sector": _safe_str(info.get("sector")),
                        "industry": _safe_str(info.get("industry")),
                    }
                    overview["sources_used"].append("yfinance")
            except Exception as e:
                logger.warning(f"yfinance フォールバック失敗: {e}")

        if not overview.get("company") and not overview.get("market_data"):
            overview["message"] = "該当する銘柄情報が見つかりませんでした。"

        return json.dumps(overview, ensure_ascii=False, indent=2, default=str)

    finally:
        db.close()


# =====================================================
# エントリーポイント
# =====================================================

if __name__ == "__main__":
    # stdio トランスポートでMCPサーバーを起動
    mcp.run()
