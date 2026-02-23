"""
EDINET 差分比較ルーター

htmx パーシャルとして差分サマリーを返す。
ファンダメンタル分析ページから hx-get で呼び出される。
"""

from fastapi import APIRouter, Request, Depends, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
import logging

from database import get_db
from services.edinet_diff_service import get_or_generate_diff

router = APIRouter(tags=["edinet_diff"])
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger(__name__)


def _format_number(value):
    """数値をカンマ区切りでフォーマットする（テンプレートフィルター用）"""
    if value is None or value == "—":
        return "—"
    try:
        num = float(str(value))
        # 百万円単位に変換して表示
        millions = num / 1_000_000
        if abs(millions) >= 1:
            return f"{millions:,.0f}"
        else:
            return f"{num:,.0f}"
    except (ValueError, TypeError):
        return str(value)


def _format_pct(value):
    """パーセンテージをフォーマット（テンプレートフィルター用）"""
    if value is None:
        return "—"
    try:
        pct = float(value) * 100
        sign = "+" if pct > 0 else ""
        return f"{sign}{pct:.1f}%"
    except (ValueError, TypeError):
        return "—"


def _format_delta(value):
    """差分をフォーマット（テンプレートフィルター用）"""
    if value is None or value == "—":
        return "—"
    try:
        num = float(str(value))
        millions = num / 1_000_000
        sign = "+" if num > 0 else ""
        if abs(millions) >= 1:
            return f"{sign}{millions:,.0f}"
        else:
            return f"{sign}{num:,.0f}"
    except (ValueError, TypeError):
        return str(value)


# テンプレートフィルターを登録
templates.env.filters["fmt_num"] = _format_number
templates.env.filters["fmt_pct"] = _format_pct
templates.env.filters["fmt_delta"] = _format_delta


@router.get("/partials/edinet/diff_summary", response_class=HTMLResponse)
async def get_diff_summary_partial(
    request: Request,
    doc_id: str = Query(..., description="対象書類の doc_id"),
    force: bool = Query(False, description="キャッシュを無視して再生成"),
    db: Session = Depends(get_db),
):
    """
    EDINET 差分サマリーの htmx パーシャルを返す。
    生成済キャッシュがあればそれを表示、無ければ生成→保存→表示。
    """
    try:
        diff_data = get_or_generate_diff(db, doc_id, force=force)

        return templates.TemplateResponse(
            "partials/edinet/_diff_summary.html",
            {
                "request": request,
                "diff": diff_data,
                "doc_id": doc_id,
            },
        )
    except Exception as e:
        logger.error(f"差分サマリー生成エラー doc_id={doc_id}: {e}", exc_info=True)
        return templates.TemplateResponse(
            "partials/edinet/_diff_summary.html",
            {
                "request": request,
                "diff": {
                    "status": "failed",
                    "notes": f"差分サマリーの生成中にエラーが発生しました: {e}",
                    "current_doc_id": doc_id,
                },
                "doc_id": doc_id,
            },
        )
