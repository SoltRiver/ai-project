
import os
import hashlib
from datetime import datetime, date
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from typing import Optional, Union

from models.edinet_file import EdinetFile
from database import SessionLocal
import logging

logger = logging.getLogger(__name__)

# Fixed storage root
# Allow override for Docker (default to D:\edinet_data for local)
BASE_STORAGE_DIR = Path(os.getenv("EDINET_STORAGE_DIR", r"D:\edinet_data"))

class EdinetStorageService:
    def __init__(self, db: Session = None):
        self.db = db or SessionLocal()

    def _get_doc_dir(self, doc_id: str, date_obj: datetime) -> Path:
        """
        Constructs directory path: D:\edinet_data\{YYYY}\{MM}\{doc_id}
        """
        year = date_obj.strftime("%Y")
        month = date_obj.strftime("%m")
        return BASE_STORAGE_DIR / year / month / doc_id

    def ensure_directory(self, doc_id: str, date_obj: datetime) -> Path:
        """
        Creates raw/extracted/derived directories.
        Returns the doc_id root directory.
        """
        doc_root = self._get_doc_dir(doc_id, date_obj)
        (doc_root / "raw").mkdir(parents=True, exist_ok=True)
        # We don't create extracted/derived eagerly, only when needed as per specs
        # But user said "Download before always create: ...\raw"
        return doc_root

    def _calculate_sha256(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    def save_raw_file(self, 
                      doc_id: str, 
                      date_obj: datetime, 
                      file_type: str, 
                      content: bytes,
                      submitter_code: Optional[str] = None,
                      doc_type_code: Optional[str] = None,
                      period_end: Optional[Union[date, str]] = None
                      ) -> EdinetFile:
        """
        Saves raw file to D:\edinet_data\... and updates DB.
        Idempotent: Overwrites file, updates DB record.
        """
        # Determine filename based on type
        filename_map = {
            "ZIP_TYPE1": "edinet_type1.zip",
            "PDF_TYPE2": "edinet_type2.pdf",
            "ZIP_TYPE3": "edinet_type3.zip",
            "ZIP_TYPE4": "edinet_type4.zip",
            "ZIP_TYPE5": "edinet_type5.zip"
        }
        
        filename = filename_map.get(file_type)
        if not filename:
            raise ValueError(f"Unknown file_type: {file_type}")

        # Directory
        doc_root = self.ensure_directory(doc_id, date_obj)
        raw_dir = doc_root / "raw"
        file_path = raw_dir / filename
        
        # Save File
        with open(file_path, "wb") as f:
            f.write(content)
            
        # Calculate Metadata
        size = len(content)
        sha256_hash = self._calculate_sha256(content)
        
        # Relative Path for DB
        # relative_to needs to be relative to BASE_STORAGE_DIR
        relative_path = str(file_path.relative_to(BASE_STORAGE_DIR))
        
        # DB Upsert
        # Check if exists
        db = self.db # Use self.db (SessionLocal was imported but self.db is instance)
        try:
            existing = db.query(EdinetFile).filter_by(doc_id=doc_id, file_type=file_type).first()
            
            p_end = None
            if period_end:
                 if isinstance(period_end, str):
                     try:
                         p_end = datetime.strptime(period_end, "%Y-%m-%d").date()
                     except:
                         pass
                 else:
                     p_end = period_end

            if existing:
                existing.storage_path = relative_path
                existing.file_size = size
                existing.sha256 = sha256_hash
                existing.status = "OK"
                existing.updated_at = datetime.now()
                # Update metadata if provided
                if submitter_code: existing.submitter_code = submitter_code
                if doc_type_code: existing.doc_type_code = doc_type_code
                if p_end: existing.period_end = p_end
                
                db.commit()
                db.refresh(existing)
                logger.info(f"Updated EDINET file record: {doc_id} / {file_type}")
                return existing
            else:
                new_record = EdinetFile(
                    doc_id=doc_id,
                    file_type=file_type,
                    storage_path=relative_path,
                    file_size=size,
                    sha256=sha256_hash,
                    status="OK",
                    submitter_code=submitter_code,
                    doc_type_code=doc_type_code,
                    period_end=p_end
                )
                db.add(new_record)
                db.commit()
                db.refresh(new_record)
                logger.info(f"Created EDINET file record: {doc_id} / {file_type}")
                return new_record
        except Exception as e:
            logger.error(f"DB Error saving {doc_id}: {e}")
            db.rollback()
            raise e

    def get_absolute_path(self, storage_path: str) -> Path:
        """Utility to convert DB relative path to absolute path."""
        return BASE_STORAGE_DIR / storage_path

    def get_file_record(self, doc_id: str, file_type: str) -> Optional[EdinetFile]:
        return self.db.query(EdinetFile).filter_by(doc_id=doc_id, file_type=file_type).first()
