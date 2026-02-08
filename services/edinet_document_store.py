
import os
import shutil
import zipfile
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class EdinetDocumentStore:
    def __init__(self, base_dir: Optional[str] = None):
        """
        Initialize document store.
        Args:
            base_dir: Root directory for data. Defaults to EDINET_DATA_DIR env or ./data/edinet
        """
        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            env_dir = os.environ.get("EDINET_DATA_DIR")
            if env_dir:
                self.base_dir = Path(env_dir)
            else:
                self.base_dir = Path("data/edinet")
                
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
    def get_doc_dir(self, doc_id: str) -> Path:
        return self.base_dir / doc_id

    def save_document(self, doc_id: str, binary_content: bytes) -> Path:
        """
        Save ZIP binary to {base}/{doc_id}/{doc_id}.zip
        """
        doc_dir = self.get_doc_dir(doc_id)
        doc_dir.mkdir(parents=True, exist_ok=True)
        
        zip_path = doc_dir / f"{doc_id}.zip"
        with open(zip_path, "wb") as f:
            f.write(binary_content)
            
        logger.info(f"Saved document ZIP to {zip_path}")
        return zip_path

    def extract_document(self, doc_id: str, force: bool = False) -> Path:
        """
        Extract ZIP to {base}/{doc_id}/unzipped/
        
        Args:
            doc_id: Document ID
            force: If True, remove existing unzipped dir and re-extract
            
        Returns:
            Path: Path to unzipped directory
            
        Raises:
            ValueError: If ZIP not found or zip-slip detected
        """
        doc_dir = self.get_doc_dir(doc_id)
        zip_path = doc_dir / f"{doc_id}.zip"
        extract_dir = doc_dir / "unzipped"
        
        if not zip_path.exists():
            raise ValueError(f"ZIP file not found for {doc_id}")
            
        if extract_dir.exists():
            if force:
                shutil.rmtree(extract_dir)
            else:
                logger.info(f"Document {doc_id} already extracted.")
                return extract_dir
                
        extract_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Zip-slip protection
                for member in zip_ref.namelist():
                    member_path = (extract_dir / member).resolve()
                    if not str(member_path).startswith(str(extract_dir.resolve())):
                        logger.error(f"Zip-slip attempt detected: {member}")
                        raise ValueError(f"Zip-slip attempt detected: {member}")
                        
                zip_ref.extractall(extract_dir)
                logger.info(f"Extracted {doc_id} to {extract_dir}")
                
        except zipfile.BadZipFile:
            logger.error(f"Bad ZIP file: {zip_path}")
            if extract_dir.exists():
                shutil.rmtree(extract_dir)
            raise ValueError("Corrupted ZIP file")
            
        return extract_dir
