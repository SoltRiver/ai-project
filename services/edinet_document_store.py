import os
import shutil
import zipfile
import logging
from pathlib import Path
from typing import Optional, Any

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
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
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

    def find_latest_local_xbrl(self, stock_code: str) -> Optional[dict[str, Any]]:
        """
        Find the latest locally extracted XBRL document for the given stock code.
        Returns the extracted financial data.

        Args:
            stock_code: Stock code (e.g. "8306")

        Returns:
            dict[str, Any] (financials) or None
        """
        # Late import to avoid circular dependency
        from services.edinet_xbrl_locator import EdinetXbrlLocator
        from services.edinet_fin_extract import EdinetFinancialExtractor
        import asyncio

        candidates = []

        # Iterate all subdirectories in base_dir
        for item in self.base_dir.iterdir():
            if item.is_dir():
                doc_id = item.name
                # Check if it has unzipped content
                unzipped_dir = item / "unzipped"
                if unzipped_dir.exists():
                    try:
                        # Simplified locator logic: find largest .xbrl in XBRL/PublicDoc
                        xbrl_files = list(unzipped_dir.rglob("*.xbrl"))
                        if not xbrl_files:
                            continue

                        # Sort by size (largest is usually main)
                        xbrl_files.sort(key=lambda p: p.stat().st_size, reverse=True)
                        target_xbrl = xbrl_files[0]

                        extractor = EdinetFinancialExtractor()
                        data = extractor.extract_financials(str(target_xbrl))

                        extracted_code = data.get("sec_code")
                        if extracted_code:
                            # Normalize (remove Zeros or match)
                            if extracted_code.startswith(stock_code):
                                # Add doc_id to data for reference
                                data["doc_id"] = doc_id
                                candidates.append(
                                    (doc_id, data.get("period_end"), data)
                                )

                    except Exception as e:
                        continue

        if not candidates:
            return None

        # Sort by period_end (descending)
        def sort_key(item):
            d_str = item[1]
            if d_str:
                return d_str
            return "0000-00-00"

        candidates.sort(key=sort_key, reverse=True)

        # Return data of best match
        return candidates[0][2]
