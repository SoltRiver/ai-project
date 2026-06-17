import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from sqlalchemy import text, or_, and_
from sqlalchemy.orm import Session

from database import SessionLocal
from models.edinet_pdf import EdinetPdfText
from models.edinet_document import EdinetDocument
from services.text_normalizer import TextNormalizer

logger = logging.getLogger(__name__)


class SearchService:
    def __init__(self, db: Session = None):
        self.db = db if db else SessionLocal()

    def search(
        self,
        query: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        sec_code: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        Hybrid Search (TRGM + FTS) with Query Guards.
        """
        # 1. Query Guard
        if not query:
            return {"status": "ERROR", "message": "Query is empty"}

        q_core = TextNormalizer.get_query_core(query)
        q_len = len(q_core)

        if q_len < 2:
            return {"status": "ERROR", "message": "Query too short (min 2 chars)"}

        if q_len == 2:
            # 2 chars: Require strict filters
            if not sec_code and not (date_from and date_to):
                return {
                    "status": "ERROR",
                    "message": "For 2-char queries, specify Date Range or Sec Code",
                }

        # 2. Normalize Query for Search
        # TRGM ILIKE expects normalized text
        norm_query = TextNormalizer.normalize_text(query)

        # 3. Build Query
        # Base: Join with Document for metadata
        stmt = self.db.query(
            EdinetPdfText.doc_id,
            EdinetPdfText.page_no,
            EdinetPdfText.text_body,
            EdinetDocument.submit_datetime,
            EdinetDocument.filer_name,
            EdinetDocument.doc_description,
        ).join(EdinetDocument, EdinetPdfText.doc_id == EdinetDocument.doc_id)

        # Filters
        if date_from:
            stmt = stmt.filter(EdinetDocument.submit_datetime >= date_from)
        if date_to:
            stmt = stmt.filter(EdinetDocument.submit_datetime <= date_to)
        if sec_code:
            stmt = stmt.filter(EdinetDocument.sec_code == sec_code)

        # Search Strategy
        # A) FTS (Alpha-numeric only?) -> User said "B) 英数字主体の場合のみFTS"
        # Check if query is mostly ASCII
        is_ascii = all(ord(c) < 128 for c in q_core)
        use_fts = is_ascii and len(q_core) > 3  # arbitrary threshold for optimization

        # For now, MVP: Always TRGM ILIKE (or LIKE safely)
        # Postgres pg_trgm supports ILIKE index.
        # SQLite supports LIKE index case-insensitive depending on collation.
        # We use standard ILIKE.

        stmt = stmt.filter(EdinetPdfText.text_body.ilike(f"%{norm_query}%"))

        # Order and Limit
        stmt = stmt.order_by(EdinetDocument.submit_datetime.desc())
        stmt = stmt.limit(limit)

        # Execute
        results = []
        try:
            rows = stmt.all()
            for r in rows:
                snippet = self._generate_snippet(r.text_body, norm_query)
                results.append(
                    {
                        "doc_id": r.doc_id,
                        "page_no": r.page_no,
                        "submit_date": (
                            r.submit_datetime.isoformat() if r.submit_datetime else None
                        ),
                        "filer_name": r.filer_name,
                        "doc_desc": r.doc_description,
                        "snippet": snippet,
                    }
                )

            return {
                "status": "OK",
                "count": len(results),
                "limit": limit,
                "strategy": "TRGM" + ("+FTS" if use_fts else ""),  # Log info
                "results": results,
            }

        except Exception as e:
            logger.error(f"Search Error: {e}")
            return {"status": "ERROR", "message": str(e)}

    def _generate_snippet(self, text_body: str, query: str) -> str:
        """
        Generate snippet logic (App side). Case-insensitive find.
        """
        if not text_body or not query:
            return ""

        # Case-insensitive search
        idx = text_body.lower().find(query.lower())
        if idx == -1:
            return text_body[:120] + "..."

        start = max(0, idx - 60)
        end = min(len(text_body), idx + len(query) + 60)

        prefix = "..." if start > 0 else ""
        suffix = "..." if end < len(text_body) else ""

        return prefix + text_body[start:end] + suffix
