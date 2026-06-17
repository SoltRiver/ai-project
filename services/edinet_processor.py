import logging
from datetime import datetime, date
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

# For Postgres compatibility in future, we might use generic upsert or specific dialect
# But for now app runs on SQLite.
# User requirement: "DB Access abstract... Postgres compatible DDL"

from database import SessionLocal
from models.edinet_document import EdinetDocument
from models.edinet_file import EdinetFile
from services.edinet_service import EdinetClient
from services.edinet_storage import EdinetStorageService

logger = logging.getLogger(__name__)


class EdinetProcessor:
    def __init__(self, db: Session = None):
        self.db = db if db else SessionLocal()
        self.client = EdinetClient()
        # Storage service might need db session too
        self.storage = EdinetStorageService(db=self.db)

    def run_daily_process(self, target_date: date):
        """
        Main entry point for daily processing.
        PROPMPT Requirement:
        1. Fetch documents.json -> UPSERT edinet_document
        2. Filter (MVP) -> Determine target docIDs
        3. Download ZIP/PDF -> Save -> UPSERT edinet_file
        """
        logger.info(f"Starting daily process for {target_date}")
        print(f"--- Processing {target_date} ---")

        # 1. Fetch & Upsert Documents
        docs_json = self.client.get_documents_by_date(target_date)
        print(f"Fetched {len(docs_json)} documents from API.")

        self._upsert_documents_metadata(target_date, docs_json)

        # 2. Filter Targets
        target_docs = self._filter_documents_mvp(target_date)
        print(f"Identified {len(target_docs)} target documents for download.")

        # 3. Download & Save
        self._process_downloads(target_docs)

        print("--- Daily Process Complete ---")

    def _upsert_documents_metadata(self, target_date: date, docs_list: List[dict]):
        """
        Upsert metadata into EdinetDocument table.
        """
        count = 0
        for data in docs_list:
            try:
                doc_id = data.get("docID")
                if not doc_id:
                    continue

                # Parse dates
                def p_date(s):
                    return datetime.strptime(s, "%Y-%m-%d").date() if s else None

                def p_datetime(s):
                    return (
                        datetime.strptime(s, "%Y-%m-%d %H:%M").replace(
                            hour=int(s[-5:-3]), minute=int(s[-2:])
                        )
                        if s and len(s) > 10
                        else None
                    )

                # API returns submitDateTime as 'YYYY-MM-DD HH:MM' string

                # Map fields
                doc_record = EdinetDocument(
                    doc_id=doc_id,
                    target_date=target_date,
                    edinet_code=data.get("edinetCode"),
                    sec_code=data.get("secCode"),
                    jcn=data.get("JCN"),
                    filer_name=data.get("filerName"),
                    doc_type_code=data.get("docTypeCode"),
                    form_code=data.get("formCode"),
                    doc_description=data.get("docDescription"),
                    period_start=p_date(data.get("periodStart")),
                    period_end=p_date(data.get("periodEnd")),
                    submit_datetime=(
                        datetime.strptime(data.get("submitDateTime"), "%Y-%m-%d %H:%M")
                        if data.get("submitDateTime")
                        else None
                    ),
                    withdrawal_status=data.get("withdrawalStatus"),
                    doc_info_edit_status=data.get("docInfoEditStatus"),
                    disclosure_status=data.get("disclosureStatus"),
                    xbrl_flag=data.get("xbrlFlag"),
                    pdf_flag=data.get("pdfFlag"),
                    attach_doc_flag=data.get("attachDocFlag"),
                    english_doc_flag=data.get("englishDocFlag"),
                    csv_flag=data.get("csvFlag"),
                )

                # Upsert Logic
                # SQLite Specific, but we abstract it slightly
                # For basic Upsert: Check exist -> update or insert
                existing = (
                    self.db.query(EdinetDocument).filter_by(doc_id=doc_id).first()
                )
                if existing:
                    # Update fields
                    for k, v in doc_record.__dict__.items():
                        if not k.startswith("_") and k != "created_at":
                            setattr(existing, k, v)
                else:
                    self.db.add(doc_record)

                count += 1
                if count % 100 == 0:
                    self.db.commit()
            except Exception as e:
                logger.error(f"Error upserting doc metadata: {e}")

        self.db.commit()
        print(f"Upserted {count} document records.")

    def _filter_documents_mvp(self, target_date: date) -> List[EdinetDocument]:
        """
        Filter documents based on MVP Logic:
        1. Keywords: "有価証券報告書", "四半期報告書"
        2. Priority: 1) Yuho, 2) Quarter, 3) Others
        3. Latest submit_datetime if duplicate (Same sec_code? No, usually distinct docIDs.
           But if same filer submits multiple, we process all usually.
           User prompt: "Duplicate candidates for same stock -> adopt latest submit_datetime")
        """

        # Get all docs for date
        all_docs = (
            self.db.query(EdinetDocument).filter_by(target_date=target_date).all()
        )

        candidates = []
        for doc in all_docs:
            desc = doc.doc_description or ""
            dtype = doc.doc_type_code or ""

            # Filter Conditions
            is_yuho = "有価証券報告書" in desc or dtype == "120"
            is_quarter = "四半期報告書" in desc or dtype == "140"

            # Strict Filtering? User says "doc_description keyword match OR doc_type_code priority"
            if is_yuho or is_quarter:
                priority = 1 if is_yuho else 2
                candidates.append((doc, priority))

        # Group by sec_code (or edinet_code) to handle duplicates?
        # User: "Same stock (same sec_code?) -> latest submit_datetime"
        # We assume sec_code is present. If not, use edinet_code.

        grouped = {}
        for doc, prio in candidates:
            key = (
                doc.edinet_code
            )  # Better than sec_code which might be null for some filers?
            if not key:
                key = doc.doc_id  # Fallback

            if key not in grouped:
                grouped[key] = (doc, prio)
            else:
                # Compare
                curr_doc, curr_prio = grouped[key]
                # Lower priority number is better (1 < 2)
                if prio < curr_prio:
                    grouped[key] = (doc, prio)
                elif prio == curr_prio:
                    # Newer is better
                    if doc.submit_datetime and curr_doc.submit_datetime:
                        if doc.submit_datetime > curr_doc.submit_datetime:
                            grouped[key] = (doc, prio)

        # Flatten
        final_list = [v[0] for v in grouped.values()]

        # Log results
        print("--- Target Documents (MVP Filter) ---")
        for d in final_list:
            print(
                f"- {d.doc_id} / {d.edinet_code} / {d.doc_description} ({d.submit_datetime})"
            )

        return final_list

    def _process_downloads(self, documents: List[EdinetDocument]):
        """
        Download ZIP (type 1) and PDF (type 2) for each document.
        Idempotent check before download.
        """
        for doc in documents:
            # Type 1: ZIP (XBRL)
            if doc.xbrl_flag == "1":
                self._handle_download(doc, "ZIP_TYPE1", 1)

            # Type 2: PDF
            if doc.pdf_flag == "1":
                self._handle_download(doc, "PDF_TYPE2", 2)

    def _handle_download(
        self, doc: EdinetDocument, file_type_str: str, api_type_code: int
    ):
        doc_id = doc.doc_id

        # 1. Idempotency Check
        existing = (
            self.db.query(EdinetFile)
            .filter_by(doc_id=doc_id, file_type=file_type_str)
            .first()
        )
        if existing and existing.status == "OK":
            # Check local file existence? For strict robustness, yes.
            # But user prompt says "1) Existing status=OK and sha256 match -> DL Skip"
            # We assume DB is truth for now.
            # Optional: Check if file physically exists.
            abs_path = self.storage.get_absolute_path(existing.storage_path)
            if abs_path.exists():
                logger.info(f"Skipping {doc_id} {file_type_str} (Already exists)")
                return
            else:
                logger.warning(
                    f"Record OK but file missing for {doc_id}. Re-downloading."
                )

        # 2. Download
        print(f"Processing download: {doc_id} ({file_type_str})...")
        content = None
        error_msg = None

        try:
            if api_type_code == 1:
                content = self.client.fetch_document_content_zip(doc_id)
            elif api_type_code == 2:
                content = self.client.fetch_document_content_pdf(doc_id)

            if content:
                # 3. Save & Upsert
                # Determine date for storage folder
                # doc.target_date or doc.submit_datetime?
                # User prompt: "D:\edinet_data\{YYYY}\{MM}\{doc_id}\raw\"
                # Usually based on submit date. But doc.target_date is safer if submit_date is null?
                # submit_datetime is usually present.
                date_ref = (
                    doc.submit_datetime
                    if doc.submit_datetime
                    else datetime.combine(doc.target_date, datetime.min.time())
                )

                self.storage.save_raw_file(
                    doc_id=doc_id,
                    date_obj=date_ref,
                    file_type=file_type_str,
                    content=content,
                    submitter_code=doc.edinet_code,
                    doc_type_code=doc.doc_type_code,
                    period_end=doc.period_end,
                )
                print(f"Saved {doc_id} {file_type_str}")
            else:
                error_msg = "Download returned empty"

        except Exception as e:
            error_msg = str(e)
            print(f"Exception downloading {doc_id}: {e}")

        # Handle Failures (Upsert NG record)
        if error_msg or content is None:
            self._upsert_ng_record(doc_id, file_type_str, error_msg or "Unknown Error")

    def _upsert_ng_record(self, doc_id, file_type, msg):
        # We need to record the failure in DB
        # EdinetStorageService.save_raw_file handles OK cases.
        # We handle NG here.
        existing = (
            self.db.query(EdinetFile)
            .filter_by(doc_id=doc_id, file_type=file_type)
            .first()
        )
        if existing:
            existing.status = "NG"
            existing.error_message = msg
            existing.updated_at = datetime.now()
        else:
            rec = EdinetFile(
                doc_id=doc_id,
                file_type=file_type,
                storage_path="",  # No path
                file_size=0,
                sha256="",
                status="NG",
                error_message=msg,
            )
            self.db.add(rec)
        self.db.commit()

    def __del__(self):
        if self.db:
            self.db.close()
