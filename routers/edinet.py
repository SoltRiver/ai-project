from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List
from schemas.response_models import EdinetDocumentsResponse, EdinetHealthResponse
from datetime import datetime
import os
import logging
from services.edinet_fetcher import fetch_and_normalize_documents
from services.edinet_client import EdinetAPIError

router = APIRouter(prefix="/edinet", tags=["edinet"])
logger = logging.getLogger(__name__)


@router.get("/documents", response_model=EdinetDocumentsResponse)
async def get_documents(
    date: str = Query(..., regex="^\d{4}-\d{2}-\d{2}$", description="YYYY-MM-DD"),
    type: int = Query(2, ge=1, le=2, description="1 or 2"),
) -> Dict[str, Any]:
    # Validate date format and future check
    try:
        req_date = datetime.strptime(date, "%Y-%m-%d")
        if req_date > datetime.now():
            raise HTTPException(status_code=400, detail="Future date not allowed.")
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid date format. Use YYYY-MM-DD."
        )

    try:
        documents = await fetch_and_normalize_documents(date, type)
        return {"date": date, "count": len(documents), "documents": documents}
    except EdinetAPIError as e:
        status_code = e.status_code if e.status_code else 502
        raise HTTPException(status_code=status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in /edinet/documents: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/health", response_model=EdinetHealthResponse)
async def health_check():
    api_key = os.environ.get("EDINET_API_KEY")
    has_key = bool(api_key)
    return {"ok": True, "has_api_key": has_key}
