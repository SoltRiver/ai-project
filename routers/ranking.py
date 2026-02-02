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
    rank_data = get_rankings(period_type="today", target_type="top")
    top_rank = rank_data.get("top", [])
    
    # 初回の更新時に重い場合はバックグラウンド等検討だが、一旦同期で分析
    ai_analysis = analyze_ranking_with_ai(top_rank, is_top=True)
    
    return templates.TemplateResponse(
        "ranking/index.html",
        {
            "request": request,
            "top_rank": top_rank,
            "period": "today",
            "rank_type": "top",
            "ai_analysis": ai_analysis,
            "page_title": "銘柄騰落ランキング",
            "last_updated": datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        }
    )

@router.get("/list", response_class=HTMLResponse)
async def ranking_list(
    request: Request,
    type: str = Query("top", enum=["top", "bottom"]),
    period: str = Query("today", enum=["today", "week", "month", "year"])
):
    """
    HTMXによる条件切り替え時のリスト部分のみを返却
    """
    rank_data = get_rankings(period_type=period, target_type=type)
    items = rank_data.get(type, [])
    
    ai_analysis = analyze_ranking_with_ai(items, is_top=(type == "top"))
    
    return templates.TemplateResponse(
        "ranking/_list.html",
        {
            "request": request,
            "items": items,
            "rank_type": type,
            "period": period,
            "ai_analysis": ai_analysis,
            "last_updated": datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        }
    )
