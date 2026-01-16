from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import logging

from services.financial_analyzer import FinancialAnalyzer


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

router = APIRouter(prefix="/stocks", tags=["stocks"])
templates = Jinja2Templates(directory="templates")
templates.env.filters["format_currency"] = format_currency
analyzer = FinancialAnalyzer()

@router.get("/{symbol}/fundamental", response_class=HTMLResponse)
async def get_fundamental_analysis(request: Request, symbol: str):
    """
    Render the Fundamental Analysis page.
    """
    # Perform analysis
    # Note: This might be slow on first load due to EDINET fetch.
    # We should probably use htmx to load it lazily if it's too slow, 
    # but for MVP synchronous is okay.
    
    try:
        data = analyzer.analyze_stock(symbol)
    except Exception as e:
        logging.error(f"Error analyzing {symbol}: {e}")
        data = {"error": str(e), "symbol": symbol}

    return templates.TemplateResponse(
        "fundamental_analysis.html",
        {"request": request, "analysis": data, "symbol": symbol}
    )
