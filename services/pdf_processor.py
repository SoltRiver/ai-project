
import logging
import io
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

from database import SessionLocal
from models.edinet_file import EdinetFile
from models.edinet_pdf import EdinetPdfText, EdinetPdfExtractStatus
from services.edinet_storage import EdinetStorageService
from services.text_normalizer import TextNormalizer

# Try importing pdfminer
try:
    from pdfminer.high_level import extract_pages
    from pdfminer.layout import LTTextContainer
    HAS_PDFMINER = True
except ImportError:
    HAS_PDFMINER = False

logger = logging.getLogger(__name__)

class PdfProcessor:
    def __init__(self, db: Session = None):
        self.db = db if db else SessionLocal()
        self.storage = EdinetStorageService(db=self.db)

    def process_document(self, doc_id: str) -> Dict[str, Any]:
        """
        Extract text from PDF (Type 2) and save to DB.
        Idempotent: Checks EdinetPdfExtractStatus.
        """
        if not HAS_PDFMINER:
            logger.error("pdfminer.six not installed.")
            return {"status": "NG", "reason": "Missing dependency"}

        # 1. Check Idempotency
        status = self.db.query(EdinetPdfExtractStatus).filter_by(doc_id=doc_id).first()
        if status and status.status == "OK":
            logger.info(f"Skipping {doc_id} (Already extracted).")
            return {"status": "SKIP", "reason": "Already processed"}

        try:
            # 2. Find PDF File
            # Look for PDF_TYPE2 with status OK
            ef = self.db.query(EdinetFile).filter_by(doc_id=doc_id, file_type="PDF_TYPE2", status="OK").first()
            if not ef:
                return self._record_status(doc_id, "SKIP", error_message="No PDF_TYPE2 found")

            pdf_path = self.storage.get_absolute_path(ef.storage_path)
            if not pdf_path.exists():
                 return self._record_status(doc_id, "NG", error_message="PDF file missing on disk")

            # 3. Extract Pages
            logger.info(f"Extracting PDF for {doc_id}...")
            pages_data = self._extract_pages(pdf_path)
            
            # 4. Save to DB
            total_chars = self._save_text(doc_id, pages_data)
            
            # 5. Success Status
            return self._record_status(doc_id, "OK", page_count=len(pages_data), total_chars=total_chars)

        except Exception as e:
            logger.error(f"PDF Extract Error {doc_id}: {e}")
            return self._record_status(doc_id, "NG", error_message=str(e))

    def _extract_pages(self, pdf_path: Path) -> List[Dict]:
        """
        Extract text page by page using low-level API to bypass permissions.
        """
        from pdfminer.converter import PDFPageAggregator
        from pdfminer.layout import LAParams, LTTextContainer
        from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
        from pdfminer.pdfpage import PDFPage

        results = []
        page_num = 1
        
        with open(pdf_path, 'rb') as fp:
            rsrcmgr = PDFResourceManager()
            laparams = LAParams()
            device = PDFPageAggregator(rsrcmgr, laparams=laparams)
            interpreter = PDFPageInterpreter(rsrcmgr, device)
            
            # check_extractable=False to bypass "PDFTextExtractionNotAllowed"
            for page in PDFPage.get_pages(fp, check_extractable=False):
                interpreter.process_page(page)
                layout = device.get_result()
                
                page_text = ""
                for element in layout:
                    if isinstance(element, LTTextContainer):
                        page_text += element.get_text()
                
                # Normalize
                norm_text = TextNormalizer.normalize_text(page_text)
                
                results.append({
                    "page_no": page_num,
                    "text": norm_text,
                    "len": len(norm_text)
                })
                page_num += 1
            
        return results

    def _save_text(self, doc_id: str, pages_data: List[Dict]) -> int:
        """
        Bulk upsert pages. Returns total chars.
        """
        total_chars = 0
        objects = []
        
        # Delete existing (if re-processing NG)
        self.db.query(EdinetPdfText).filter_by(doc_id=doc_id).delete()
        
        for p in pages_data:
            obj = EdinetPdfText(
                doc_id=doc_id,
                page_no=p["page_no"],
                text_body=p["text"],
                text_len=p["len"]
            )
            objects.append(obj)
            total_chars += p["len"]
            
        if objects:
            self.db.bulk_save_objects(objects)
            self.db.commit()
            
        return total_chars

    def _record_status(self, doc_id, status, page_count=None, total_chars=None, error_message=None):
        # Upsert status
        # Note: SQLite upsert support in simple SQLA is tricky, but here we can just delete/insert or merge.
        # EdinetPdfExtractStatus has doc_id primary key.
        
        s = self.db.merge(EdinetPdfExtractStatus(
            doc_id=doc_id,
            status=status,
            page_count=page_count,
            total_chars=total_chars,
            error_message=error_message,
            rule_version="v1",
            processed_at=datetime.now()
        ))
        self.db.commit()
        return {
            "status": status, 
            "doc_id": doc_id, 
            "page_count": page_count, 
            "total_chars": total_chars,
            "reason": error_message or "Success"
        }

    def __del__(self):
        # self.db.close() 
        pass
