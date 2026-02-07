
from services.edinet_client import EdinetClient, EdinetAPIError
from typing import Dict, Any, List, Optional
import logging

def normalize_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract and re-key a single result item from EDINET response.
    """
    return {
        "doc_id": result.get("docID"),
        "edinet_code": result.get("edinetCode"),
        "sec_code": result.get("secCode"),
        "filer_name": result.get("filerName"),
        "doc_description": result.get("docDescription"),
        "submit_date_time": result.get("submitDateTime"),
        "ordinance_code": result.get("ordinanceCode"),
        "form_code": result.get("formCode"),
        "doc_type_code": result.get("docTypeCode"),
        "period_start": result.get("periodStart"),
        "period_end": result.get("periodEnd")
    }

async def fetch_and_normalize_documents(date: str, type_code: int = 2) -> List[Dict[str, Any]]:
    client = EdinetClient()
    try:
        response_data = await client.get_documents(date, type_code)
        
        results = response_data.get("results", [])
        normalized_data = [normalize_result(item) for item in results]
        
        return normalized_data
        
    finally:
        await client.close()
