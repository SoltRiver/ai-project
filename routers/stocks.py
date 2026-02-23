from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db

from services import stock_service


def format_currency(value):
    if value is None:
        value = 0
    if isinstance(value, str):
        value = value.replace(",", "").strip()
    try:
        amount = int(float(value))
    except (TypeError, ValueError):
        amount = 0
    return f"{amount:,} 円"



templates = Jinja2Templates(directory="templates")
templates.env.filters["format_currency"] = format_currency
router = APIRouter()


@router.get("/stocks", response_class=HTMLResponse)
async def list_stocks(request: Request, db: Session = Depends(get_db)):
    stocks = stock_service.get_stock_list(db)
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
        {"name": "chart", "label": "テクニカル分析", "icon": "📈"},
        {"name": "fundamental", "label": "ファンダメンタル分析", "icon": "📊"},
        {"name": "dividend", "label": "配当", "icon": "💰"},
        {"name": "margin", "label": "需給", "icon": "⚖️"},
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
async def stock_tab(code: str, tab_name: str, request: Request, db: Session = Depends(get_db)):
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
        # Impact Bias データを注入（Phase 11）
        try:
            from services.impact_bias_service import ImpactBiasService
            impact_service = ImpactBiasService(db)
            data["impact_bias"] = impact_service.get_impact_bias(code)
        except Exception as e:
            import logging
            logging.error(f"Impact bias fetch error for {code}: {e}")
            data["impact_bias"] = None
    elif tab_name == "dividend":
        data = stock_service.get_dividend_tab(code)
        template = "stocks/partials/_tab_dividend.html"
    elif tab_name == "margin":
        # 需給タブ: 信用残の構成と相対サイズを表示
        from services.margin_service import get_margin_tab
        data = get_margin_tab(code)
        template = "stocks/partials/_tab_margin.html"
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


@router.post("/stocks/add")
async def add_stock(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    code_input = form.get("code", "").strip()

    if code_input:
        target_code = None

        # 1. Try extracting from "Name (Code)" format
        if "(" in code_input and ")" in code_input:
            parts = code_input.split("(")
            if len(parts) > 1:
                possible_code = parts[-1].replace(")", "").strip()
                # Validate if it looks like a code (digits or digits.T)
                if possible_code.isdigit() or (possible_code.endswith(".T") and possible_code[:-2].isdigit()):
                    target_code = possible_code

        # 2. If not found, check if input matches a name in the map
        if not target_code:
             from data.stock_name_mapper import STOCK_NAME_MAP
             for k, v in STOCK_NAME_MAP.items():
                 if v == code_input:
                     target_code = k
                     # Prefer 4 digit code if available
                     if k.isdigit() and len(k) == 4:
                        break
        
        # 3. If still not found, treat input as code directly
        if not target_code:
            target_code = code_input

        if target_code:
            stock_service.add_stock_to_watchlist(db, target_code)
    
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/stocks", status_code=303)


@router.post("/stocks/delete")
async def delete_stocks(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    # checkboxes with same name come as list
    codes = form.getlist("selected_stocks")
    if codes:
        stock_service.remove_stocks_from_watchlist(db, codes)
    
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/stocks", status_code=303)


from fastapi.responses import JSONResponse
from schemas.response_models import StockSearchResponse

@router.get("/api/stocks/search", response_model=StockSearchResponse)
async def search_stocks_api(q: str = ""):
    results = stock_service.search_stocks(q)
    # Format for autocomplete: "Name (Code)"
    suggestions = [f"{item['name']} ({item['code']})" for item in results]
    return JSONResponse(content={"suggestions": suggestions})

