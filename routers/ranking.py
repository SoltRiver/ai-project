from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from services.ranking_service import get_rankings, analyze_ranking_with_ai
from datetime import datetime

router = APIRouter(prefix="/ranking", tags=["ranking"])
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def ranking_index(request: Request):
    """
    ランキングメインページを表示
    """
    # 初期表示は「今日」の上昇率ランキング
    try:
        rank_data = get_rankings(period_type="today", target_type="top")
        top_rank = rank_data.get("top", [])
    except Exception as e:
        print(f"ランキング初期データ取得エラー: {e}")
        top_rank = []

    # 初回の更新時に重い場合はバックグラウンド等検討だが、一旦同期で分析
    try:
        if top_rank:
            ai_analysis = analyze_ranking_with_ai(top_rank, is_top=True)
        else:
            ai_analysis = "分析対象のデータがありません。"
    except Exception as e:
        print(f"ランキングAI分析エラー: {e}")
        ai_analysis = "AI分析の取得に失敗しました。"

    return templates.TemplateResponse(
        "ranking/index.html",
        {
            "request": request,
            "top_rank": top_rank,
            "period": "today",
            "rank_type": "top",
            "ai_analysis": ai_analysis,
            "page_title": "銘柄騰落ランキング",
            "last_updated": datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
        },
    )


@router.get("/list", response_class=HTMLResponse)
async def ranking_list(
    request: Request,
    type: str = Query("top", enum=["top", "bottom"]),
    period: str = Query("today", enum=["today", "week", "month", "year"]),
):
    """
    HTMXによる条件切り替え時のリスト部分のみを返却
    """
    try:
        rank_data = get_rankings(period_type=period, target_type=type)
        items = rank_data.get(type, [])
    except Exception as e:
        print(f"ランキングリスト取得エラー: {e}")
        items = []

    try:
        if items:
            ai_analysis = analyze_ranking_with_ai(items, is_top=(type == "top"))
        else:
            ai_analysis = "分析対象のデータがありません。"
    except Exception as e:
        print(f"ランキングリストAI分析エラー: {e}")
        ai_analysis = "AI分析の取得に失敗しました。"

    return templates.TemplateResponse(
        "ranking/_list.html",
        {
            "request": request,
            "items": items,
            "rank_type": type,
            "period": period,
            "ai_analysis": ai_analysis,
            "last_updated": datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
        },
    )
