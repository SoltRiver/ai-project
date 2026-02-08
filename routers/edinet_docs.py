
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import Dict, Any
import os
import logging
from services.edinet_client import EdinetClient, EdinetAPIError
from services.edinet_document_store import EdinetDocumentStore
from services.edinet_xbrl_locator import EdinetXbrlLocator
from services.edinet_fin_extract import EdinetFinancialExtractor

router = APIRouter(prefix="/edinet/documents", tags=["edinet_docs"])
logger = logging.getLogger(__name__)

@router.get("/{doc_id}/download")
async def download_document(doc_id: str, force: bool = False) -> Dict[str, Any]:
    """
    Download ZIP, extract, and locate XBRL.
    """
    try:
        store = EdinetDocumentStore()
        
        # Check if already processed
        try:
            unzipped_dir = store.extract_document(doc_id) # Won't re-extract if exists unless force
            if force:
                raise ValueError("Force update")
        except ValueError:
            # Need download
            client = EdinetClient()
            try:
                zip_bytes = await client.get_document_zip(doc_id)
                store.save_document(doc_id, zip_bytes)
                unzipped_dir = store.extract_document(doc_id, force=True)
            finally:
                await client.close()

        # Locate XBRL
        locator = EdinetXbrlLocator()
        location_result = await locator.locate_xbrl_files(unzipped_dir)
        
        return {
            "doc_id": doc_id,
            "saved_zip": str(store.get_doc_dir(doc_id) / f"{doc_id}.zip"),
            "unzipped_dir": str(unzipped_dir),
            "xbrl_files": location_result["xbrl_files"],
            "inline_xbrl_files": location_result.get("inline_xbrl_files", []),
            "primary_xbrl": location_result["primary_xbrl"]
        }

    except EdinetAPIError as e:
        status = e.status_code if e.status_code else 502
        raise HTTPException(status_code=status, detail=str(e))
    except Exception as e:
        logger.error(f"Download failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@router.get("/{doc_id}/financials")
async def extract_financials(doc_id: str) -> Dict[str, Any]:
    """
    Extract financials from Primary XBRL.
    Requires /download to be called first.
    """
    try:
        store = EdinetDocumentStore()
        unzipped_dir = store.extract_document(doc_id) # Throws if no ZIP
        
        locator = EdinetXbrlLocator()
        location_result = await locator.locate_xbrl_files(unzipped_dir)
        primary_xbrl = location_result.get("primary_xbrl")
        
        if not primary_xbrl:
            raise HTTPException(status_code=404, detail="Primary XBRL not found in document.")
            
        extractor = EdinetFinancialExtractor()
        # Mock extraction for now if library fails or to be safe? 
        # Plan says "Use edinet-xbrl". 
        # Ideally we should run this in a threadpool if it's CPU intensive, 
        # but for now async def will block. It's okay for an internal/admin tool.
        
        financials = extractor.extract_financials(primary_xbrl)
        
        return {
            "doc_id": doc_id,
            "primary_xbrl": primary_xbrl,
            "financials": financials,
            "note": "Experimental extraction using edinet-xbrl."
        }

    except ValueError:
        # Document not found in store
        raise HTTPException(status_code=404, detail="Document not found. Call /download first.")
    except Exception as e:
        logger.error(f"Financial extraction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
