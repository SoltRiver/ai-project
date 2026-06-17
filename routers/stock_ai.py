from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from services import stock_service
from services.langgraph.stock_news_graph import run_stock_news_workflow

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/stocks/{code}/ai/news-summary", response_class=HTMLResponse)
async def stock_ai_news_summary(
    code: str, request: Request, db: Session = Depends(get_db)
):
    """
    銘柄のニュースを取得し、LangGraphワークフローでAI要約して
    HTMLパーシャルを返すエンドポイント。
    """
    # 銘柄の存在確認
    header = stock_service.get_stock_header(code)
    if header is None:
        return templates.TemplateResponse(
            "stocks/partials/_ai_news_summary.html",
            {"request": request, "error": "銘柄が見つかりません"},
        )

    # Accept-Languageから言語を判定 (デフォルトは日本語)
    accept_language = request.headers.get("accept-language", "")
    language = "日本語"
    if accept_language:
        if "ja" not in accept_language.lower():
            language = "English"

    # LangGraphワークフロー実行 (非同期)
    state = await run_stock_news_workflow(code, language=language)

    if "error" in state:
        return templates.TemplateResponse(
            "stocks/partials/_ai_news_summary.html",
            {"request": request, "error": state["error"]},
        )

    response_data = state.get("response", {})

    return templates.TemplateResponse(
        "stocks/partials/_ai_news_summary.html",
        {
            "request": request,
            "stock": header,
            "summaries": response_data.get("items", []),
        },
    )
