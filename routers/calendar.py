"""
カレンダールーター

イベントカレンダーページ、部分テンプレート、イベント同期アクションを提供。
"""

import logging
from datetime import date, datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from models.stock import Stock
from services.event_query_service import event_query_service
from services.event_sync_service import event_sync_service

logger = logging.getLogger(__name__)
templates = Jinja2Templates(directory="templates")
router = APIRouter()


def _get_watchlist_codes(db: Session) -> List[str]:
    """ウォッチリストの銘柄コード一覧を取得"""
    stocks = db.query(Stock).all()
    return [s.code for s in stocks]


def _parse_month(month_str: Optional[str]) -> tuple:
    """month=YYYY-MM をパースして (year, month) を返す。不正値は当月。"""
    if month_str:
        try:
            parts = month_str.split("-")
            return int(parts[0]), int(parts[1])
        except (ValueError, IndexError):
            pass
    today = date.today()
    return today.year, today.month


def _parse_date_str(date_str: Optional[str], year: int, month: int) -> date:
    """
    date=YYYY-MM-DD をパースする。
    不正値 or 指定月外の場合は整合ルールに従いリセット。
    """
    if date_str:
        try:
            parsed = datetime.strptime(date_str, "%Y-%m-%d").date()
            # 指定月と一致しているか確認
            if parsed.year == year and parsed.month == month:
                return parsed
        except ValueError:
            pass

    # 整合ルール: 当月なら今日、それ以外は1日
    today = date.today()
    if today.year == year and today.month == month:
        return today
    return date(year, month, 1)


def _parse_types(types_str: Optional[str]) -> Optional[List[str]]:
    """types=EARNINGS,DIVIDEND をパース。Noneなら全種別。"""
    if not types_str:
        return None
    parts = [t.strip().upper() for t in types_str.split(",") if t.strip()]
    valid = [t for t in parts if t in ("EARNINGS", "DIVIDEND")]
    return valid if valid else None


def _build_calendar_context(
    year: int,
    month: int,
    selected_date: date,
    month_events: dict,
) -> dict:
    """月カレンダーグリッド表示用のコンテキストを構築"""
    import calendar as cal_module

    # 月の日数と開始曜日
    _, last_day = cal_module.monthrange(year, month)
    first_weekday = date(year, month, 1).weekday()  # 0=月曜

    # 前月/次月の計算
    if month == 1:
        prev_month = f"{year - 1}-12"
    else:
        prev_month = f"{year}-{month - 1:02d}"

    if month == 12:
        next_month = f"{year + 1}-01"
    else:
        next_month = f"{year}-{month + 1:02d}"

    # カレンダーセルの構築（空セルも含む）
    cells = []
    # 月曜始まりの空セル
    for _ in range(first_weekday):
        cells.append({"day": None, "is_empty": True})

    today = date.today()
    for d in range(1, last_day + 1):
        cell_date = date(year, month, d)
        day_data = month_events.get(d, {"count": 0, "tags": []})

        # 表示タグ（最大2件 + "+N"）
        tags_display = day_data["tags"][:2]
        extra_count = (
            max(0, len(day_data["tags"]) - 2) if len(day_data["tags"]) > 2 else 0
        )

        cells.append(
            {
                "day": d,
                "is_empty": False,
                "date_str": cell_date.isoformat(),
                "is_today": cell_date == today,
                "is_selected": cell_date == selected_date,
                "has_events": day_data["count"] > 0,
                "event_count": day_data["count"],
                "tags": tags_display,
                "extra_count": extra_count,
            }
        )

    # 末尾の空セル（7の倍数になるまで）
    while len(cells) % 7 != 0:
        cells.append({"day": None, "is_empty": True})

    return {
        "year": year,
        "month": month,
        "month_str": f"{year}-{month:02d}",
        "month_label": f"{year}年{month}月",
        "prev_month": prev_month,
        "next_month": next_month,
        "cells": cells,
        "selected_date": selected_date.isoformat(),
        "weekdays": ["月", "火", "水", "木", "金", "土", "日"],
    }


# ─── メインページ ──────────────────────────


@router.get("/calendar", response_class=HTMLResponse)
async def calendar_page(
    request: Request,
    month: Optional[str] = None,
    date: Optional[str] = Query(None, alias="date"),
    code: Optional[str] = None,
    types: Optional[str] = None,
    watch_only: Optional[str] = "on",
    db: Session = Depends(get_db),
):
    """カレンダーメインページ"""
    year, mon = _parse_month(month)
    selected_date = _parse_date_str(date, year, mon)
    type_list = _parse_types(types)

    # ウォッチリスト
    watchlist_codes = None
    if watch_only == "on" and not code:
        watchlist_codes = _get_watchlist_codes(db)

    # 月グリッドデータ
    month_events = event_query_service.get_month_events(
        db=db,
        year=year,
        month=mon,
        code=code,
        types=type_list,
        watchlist_codes=watchlist_codes,
    )

    # 当日リストデータ
    day_events = event_query_service.get_day_events(
        db=db,
        target_date=selected_date,
        code=code,
        types=type_list,
        watchlist_codes=watchlist_codes,
    )

    # カレンダーコンテキスト
    cal_ctx = _build_calendar_context(year, mon, selected_date, month_events)

    # フィルタ状態
    filters = {
        "code": code or "",
        "types_earnings": type_list is None or "EARNINGS" in type_list,
        "types_dividend": type_list is None or "DIVIDEND" in type_list,
        "watch_only": watch_only == "on",
    }

    return templates.TemplateResponse(
        "calendar/index.html",
        {
            "request": request,
            "page_title": "イベントカレンダー",
            "cal": cal_ctx,
            "day_events": day_events,
            "filters": filters,
        },
    )


# ─── 部分テンプレート ──────────────────────────


@router.get("/partials/calendar/day", response_class=HTMLResponse)
async def partial_day_list(
    request: Request,
    date: str = "",
    code: Optional[str] = None,
    types: Optional[str] = None,
    watch_only: Optional[str] = "on",
    db: Session = Depends(get_db),
):
    """右側当日リストのみ返す（htmx用）"""
    try:
        selected_date = (
            datetime.strptime(date, "%Y-%m-%d").date()
            if date
            else __import__("datetime").date.today()
        )
    except ValueError:
        selected_date = __import__("datetime").date.today()

    type_list = _parse_types(types)
    watchlist_codes = None
    if watch_only == "on" and not code:
        watchlist_codes = _get_watchlist_codes(db)

    day_events = event_query_service.get_day_events(
        db=db,
        target_date=selected_date,
        code=code,
        types=type_list,
        watchlist_codes=watchlist_codes,
    )

    return templates.TemplateResponse(
        "calendar/partials/_day_list.html",
        {
            "request": request,
            "day_events": day_events,
            "selected_date": selected_date.isoformat(),
        },
    )


@router.get("/partials/calendar/month_grid", response_class=HTMLResponse)
async def partial_month_grid(
    request: Request,
    month: Optional[str] = None,
    code: Optional[str] = None,
    types: Optional[str] = None,
    watch_only: Optional[str] = "on",
    db: Session = Depends(get_db),
):
    """月カレンダーグリッドのみ返す（htmx用）"""
    year, mon = _parse_month(month)
    type_list = _parse_types(types)

    watchlist_codes = None
    if watch_only == "on" and not code:
        watchlist_codes = _get_watchlist_codes(db)

    # 選択日の整合ルール
    selected_date = _parse_date_str(None, year, mon)

    month_events = event_query_service.get_month_events(
        db=db,
        year=year,
        month=mon,
        code=code,
        types=type_list,
        watchlist_codes=watchlist_codes,
    )

    cal_ctx = _build_calendar_context(year, mon, selected_date, month_events)

    # フィルタ状態
    filters = {
        "code": code or "",
        "types_earnings": type_list is None or "EARNINGS" in type_list,
        "types_dividend": type_list is None or "DIVIDEND" in type_list,
        "watch_only": watch_only == "on",
    }

    return templates.TemplateResponse(
        "calendar/partials/_month_grid.html",
        {
            "request": request,
            "cal": cal_ctx,
            "filters": filters,
        },
    )


@router.get("/partials/events/stock/{code}", response_class=HTMLResponse)
async def partial_stock_events(
    code: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """銘柄詳細ページ用イベントカード"""
    summary = event_query_service.get_stock_event_summary(db=db, code=code)

    return templates.TemplateResponse(
        "stocks/partials/_event_card.html",
        {
            "request": request,
            "code": code,
            **summary,
        },
    )


# ─── アクション ──────────────────────────


@router.post("/actions/events/refresh", response_class=HTMLResponse)
async def refresh_events(
    request: Request,
    code: Optional[str] = None,
    month: Optional[str] = None,
    types: Optional[str] = None,
    watch_only: Optional[str] = "on",
    db: Session = Depends(get_db),
):
    """
    軽量同期アクション。
    対象: code指定時はその銘柄のみ、なければウォッチ銘柄（上限200件）。
    期間: 当月〜3ヶ月先。
    同期後に月グリッド + 当日リストを含む HTML を返す。
    """
    # 対象銘柄の決定
    if code:
        target_codes = [code]
    else:
        watchlist_codes = _get_watchlist_codes(db)
        target_codes = watchlist_codes[:200]  # 安全上限

    # 期間の決定（当月1日〜3ヶ月先末日）
    today = __import__("datetime").date.today()
    from_dt = today.replace(day=1)
    # 3ヶ月先の末日
    future = today + timedelta(days=92)
    import calendar as cal_module

    _, last_day = cal_module.monthrange(future.year, future.month)
    to_dt = future.replace(day=last_day)

    # 同期実行
    try:
        sync_result = event_sync_service.sync_events(target_codes, from_dt, to_dt)
        logger.info(
            f"イベント同期完了: upserted={sync_result['upserted']}, errors={len(sync_result['errors'])}"
        )
    except Exception as e:
        logger.error(f"イベント同期エラー: {e}", exc_info=True)
        sync_result = {"upserted": 0, "errors": [str(e)]}

    # 同期後、月グリッドと当日リストを含むカレンダーを返す
    year, mon = _parse_month(month)
    selected_date = _parse_date_str(None, year, mon)
    type_list = _parse_types(types)

    watchlist_codes = None
    if watch_only == "on" and not code:
        watchlist_codes = _get_watchlist_codes(db)

    month_events = event_query_service.get_month_events(
        db=db,
        year=year,
        month=mon,
        code=code,
        types=type_list,
        watchlist_codes=watchlist_codes,
    )
    day_events = event_query_service.get_day_events(
        db=db,
        target_date=selected_date,
        code=code,
        types=type_list,
        watchlist_codes=watchlist_codes,
    )

    cal_ctx = _build_calendar_context(year, mon, selected_date, month_events)
    filters = {
        "code": code or "",
        "types_earnings": type_list is None or "EARNINGS" in type_list,
        "types_dividend": type_list is None or "DIVIDEND" in type_list,
        "watch_only": watch_only == "on",
    }

    return templates.TemplateResponse(
        "calendar/partials/_calendar_body.html",
        {
            "request": request,
            "cal": cal_ctx,
            "day_events": day_events,
            "filters": filters,
            "sync_result": sync_result,
        },
    )
