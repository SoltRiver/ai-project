from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from services.news_service import fetch_and_analyze_market_news

"""
ニュースページ用ルーター
AI分析済みのマーケットニュースを提供する。
"""

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/news")
async def news_index(request: Request):
    """
    マーケットニュース一覧を表示する。
    """
    news_items = fetch_and_analyze_market_news()
    
    return templates.TemplateResponse("news/index.html", {
        "request": request,
        "page_title": "マーケットニュース",
        "news_items": news_items
    })
