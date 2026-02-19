from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
import logging

from services.financial_analyzer import FinancialAnalyzer
from services.impact_bias_service import ImpactBiasService
from database import get_db

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
async def get_fundamental_analysis(
    request: Request, 
    symbol: str, 
    db: Session = Depends(get_db)
):
    """
    Render the Fundamental Analysis page.
    """
    # 1. Financial Analysis
    try:
        data = analyzer.analyze_stock(symbol)
    except Exception as e:
        logging.error(f"Error analyzing {symbol}: {e}")
        data = {"error": str(e), "symbol": symbol}

    # 2. Impact Bias Analysis (New Phase 11)
    impact_bias = None
    try:
        # Symbol might need normalization (e.g. 1234.T -> 1234) for DB search
        # StockNews table uses 'sec_code' which is usually 4-5 digits string.
        # analyzer.analyze_stock takes "1234" usually.
        # If symbol arrives as "1234", we use it as is.
        sec_code = symbol.replace(".T", "") 
        impact_service = ImpactBiasService(db)
        impact_bias = impact_service.get_impact_bias(sec_code)
    except Exception as e:
        logging.error(f"Error getting impact bias for {symbol}: {e}")
        # Fail gracefully, impact_bias remains None

    # doc_id を安全に抽出（financialsがNoneの場合も考慮）
    doc_id_val = "N/A"
    if isinstance(data, dict):
        fin = data.get("financials")
        if isinstance(fin, dict):
            doc_id_val = fin.get("doc_id", "N/A")

    return templates.TemplateResponse(
        "fundamental_analysis.html",
        {
            "request": request, 
            "analysis": data, 
            "symbol": symbol,
            "impact_bias": impact_bias,
            "doc_id": doc_id_val
        }
    )
