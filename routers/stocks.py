from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from services import stock_service

templates = Jinja2Templates(directory="templates")
router = APIRouter()


@router.get("/stocks", response_class=HTMLResponse)
async def list_stocks(request: Request):
    stocks = stock_service.get_stock_list()
    timestamp = stock_service.get_timestamp_label()
    return templates.TemplateResponse(
        "stocks/list.html",
        {"request": request, "stocks": stocks, "page_title": "株価リスト", "timestamp_label": timestamp},
    )


@router.get("/stocks/{code}", response_class=HTMLResponse)
async def stock_detail(code: str, request: Request):
    header = stock_service.get_stock_header(code)
    if header is None:
        raise HTTPException(status_code=404, detail="銘柄が見つかりません")

    tabs = [
        {"name": "chart", "label": "チャート", "icon": "📈"},
        {"name": "fundamental", "label": "ファンダメンタル", "icon": "📊"},
        {"name": "dividend", "label": "配当", "icon": "💰"},
        {"name": "shareholder", "label": "株主優待", "icon": "🎁"},
    ]

    return templates.TemplateResponse(
        "stocks/detail.html",
        {
            "request": request,
            "stock": header,
            "tabs": tabs,
            "page_title": "株価情報詳細",
        },
    )


@router.get("/stocks/{code}/tab/{tab_name}", response_class=HTMLResponse)
async def stock_tab(code: str, tab_name: str, request: Request):
    header = stock_service.get_stock_header(code)
    if header is None:
        raise HTTPException(status_code=404, detail="銘柄が見つかりません")

    tab_name = tab_name.lower()
    if tab_name == "chart":
        interval = request.query_params.get("interval", "1d")
        data = stock_service.get_chart_tab(code, interval=interval)
        template = "stocks/partials/_tab_chart.html"
    elif tab_name == "fundamental":
        data = stock_service.get_fundamental_tab(code)
        template = "stocks/partials/_tab_fundamental.html"
    elif tab_name == "dividend":
        data = stock_service.get_dividend_tab(code)
        template = "stocks/partials/_tab_dividend.html"
    elif tab_name == "shareholder":
        data = stock_service.get_shareholder_tab(code)
        template = "stocks/partials/_tab_shareholder.html"
    else:
        raise HTTPException(status_code=404, detail="タブが見つかりません")

    return templates.TemplateResponse(template, {"request": request, "stock": header, **data})


@router.get("/glossary", response_class=HTMLResponse)
async def glossary(request: Request):
    terms = stock_service.get_glossary_terms()
    return templates.TemplateResponse(
        "glossary/glossary.html",
        {"request": request, "page_title": "用語集", "terms": terms},
    )


@router.get("/candle-patterns", response_class=HTMLResponse)
async def candle_patterns(request: Request):
    patterns = stock_service.get_candle_patterns_page()
    tab = request.query_params.get("tab", "basic")
    if tab not in patterns.get("group_labels", {}):
        tab = "basic"
    context = {"request": request, "page_title": "ローソク足パターン", "active_tab": tab, **patterns}
    if request.headers.get("HX-Request") == "true":
        return templates.TemplateResponse("candle_patterns/partials/_list_area.html", context)
    return templates.TemplateResponse("candle_patterns/index.html", context)
