
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Dict, Any, Optional
from schemas.response_models import EdinetFundamentalResponse
import logging
from services.edinet_client import EdinetClient
from services.edinet_document_store import EdinetDocumentStore
from services.edinet_xbrl_locator import EdinetXbrlLocator
from services.edinet_fin_extract import EdinetFinancialExtractor
from services.jquants_market_fetcher import JQuantsMarketFetcher
from services.fundamental_ratios import FundamentalRatios

router = APIRouter(prefix="/fundamentals", tags=["fundamentals"])
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger(__name__)

# Helper for template formatting
def format_currency(value):
    if value is None: return "-"
    try:
        if isinstance(value, str): value = float(value)
        return f"{int(value):,}"
    except:
        return value

templates.env.filters["format_currency"] = format_currency

@router.get("/reports/{doc_id}", response_class=HTMLResponse)
async def get_fundamental_report(request: Request, doc_id: str):
    """
    Render Fundamental Analysis Report (HTML).
    """
    try:
        # Recycle the logic from the API endpoint
        data = await get_edinet_fundamental(doc_id, with_market=True)
        
        return templates.TemplateResponse("fundamental_analysis.html", {
            "request": request, 
            "analysis": data,
            "doc_id": doc_id
            # Note: Template expects `analysis` object with fields like `financials`, `market`, `ratios`
        })
    except HTTPException as e:
        return templates.TemplateResponse("fundamental_analysis.html", {
            "request": request,
            "error": e.detail,
            "doc_id": doc_id
        }, status_code=e.status_code)
    except Exception as e:
        logger.error(f"Report render failed: {e}")
        return templates.TemplateResponse("fundamental_analysis.html", {
            "request": request,
            "error": "システムエラーが発生しました。",
            "doc_id": doc_id
        }, status_code=500)

@router.get("/edinet/{doc_id}", response_model=EdinetFundamentalResponse)
async def get_edinet_fundamental(doc_id: str, with_market: bool = False):
    """
    Get fundamental data from EDINET document.
    Optionally merge with J-Quants market data (price, per, pbr).
    """
    try:
        # 1. Fetch/Extract Financials
        store = EdinetDocumentStore()
        try:
            unzipped_dir = store.extract_document(doc_id)
        except ValueError:
            # Document not found locally, try to download
            client = EdinetClient()
            try:
                zip_bytes = await client.get_document_zip(doc_id)
                store.save_document(doc_id, zip_bytes)
                unzipped_dir = store.extract_document(doc_id, force=True)
            except Exception as dl_err:
                 logger.error(f"Auto-download failed for {doc_id}: {dl_err}")
                 raise HTTPException(status_code=404, detail="Document not found and download failed.")
            finally:
                await client.close()

        locator = EdinetXbrlLocator()
        location_result = await locator.locate_xbrl_files(unzipped_dir)
        primary_xbrl = location_result.get("primary_xbrl")
        
        if not primary_xbrl:
            raise HTTPException(status_code=404, detail="Primary XBRL not found in document.")

        extractor = EdinetFinancialExtractor()
        financials = extractor.extract_financials(primary_xbrl)
        
        result = {
            "doc_id": doc_id,
            "sec_code": financials.get("sec_code"),
            "financials": financials,
            "market": None,
            "ratios": None,
            "meta": {}
        }

        # 2. Market Data & Ratios
        if with_market:
            sec_code = financials.get("sec_code")
            period_end = financials.get("period_end")
            
            if sec_code:
                try:
                    # J-Quants API typically uses 5 digits now? or 4?
                    # We try as is.
                    market_fetcher = JQuantsMarketFetcher()
                    market_data = market_fetcher.get_market_data(sec_code, period_end)
                    result["market"] = market_data
                    
                    # Calculate Ratios
                    ratio_calc = FundamentalRatios()
                    ratios = ratio_calc.calculate_ratios(financials, market_data)
                    result["ratios"] = ratios
                    
                    # Meta info about calculation
                    result["meta"]["notes"] = "Market data fetched from J-Quants. Ratios calculated based on period_end close price (approx)."
                except Exception as jq_err:
                     logger.warning(f"J-Quants fetch failed: {jq_err}")
                     result["meta"]["warning"] = f"Market data unavailable (J-Quants Error: {jq_err})"
                     result["market"] = None
                     result["ratios"] = None
            else:
                 result["meta"]["warning"] = "Security code could not be extracted from XBRL. Market data unavailable."

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in fundamentals API for {doc_id}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
