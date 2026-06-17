"""
ニュースページ用ルーター
DB保存済みのニュース・AI要約結果を即時表示する。
AI呼び出しは行わない。
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from services.news_service import get_news_for_display

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/news", response_class=HTMLResponse)
async def news_index(request: Request, db: Session = Depends(get_db)):
    """
    マーケットニュース一覧を表示する。
    DBからのみデータ取得し、即時レスポンスを返す。
    AI処理はバックグラウンドバッチで別途実行される。
    """
    try:
        news_items = get_news_for_display(db, limit=15)
    except Exception as e:
        # DB読み込みエラーでもページは表示する
        import logging

        logging.getLogger(__name__).error(f"ニュース取得エラー: {e}")
        news_items = []

    return templates.TemplateResponse(
        "news/index.html",
        {
            "request": request,
            "page_title": "マーケットニュース",
            "news_items": news_items,
        },
    )
