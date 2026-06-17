from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from services.market_indices import get_major_indices

"""
主要指標の表示に関連するルーター定義。
"""

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/indices", response_class=HTMLResponse)
async def indices_view(request: Request):
    """
    主要指標一覧ページを表示します。
    """
    indices = get_major_indices()
    return templates.TemplateResponse(
        "indices/index.html",
        {"request": request, "indices": indices, "page_title": "主要指標一覧"},
    )
