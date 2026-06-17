import os
import sys
import shutil
import zipfile
import json
from datetime import datetime
from pathlib import Path

# Add project root
sys.path.insert(0, ".")

from database import SessionLocal
from models.edinet_file import EdinetFile
from models.edinet_xbrl_fact import EdinetXbrlFact
from services.xbrl_processor import XbrlProcessor
from services.edinet_storage import BASE_STORAGE_DIR


def create_dummy_data(doc_id="TEST9999"):
    # 1. Prepare Directory
    year = "2024"
    month = "01"
    doc_dir = BASE_STORAGE_DIR / year / month / doc_id
    raw_dir = doc_dir / "raw"
    if doc_dir.exists():
        shutil.rmtree(doc_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)

    # 2. Create Dummy XBRL ZIP
    xbrl_content = """<?xml version="1.0" encoding="UTF-8"?>
<xbrl xmlns="http://www.xbrl.org/2003/instance" xmlns:jppfs_cor="http://disclosure.edinet-fsa.go.jp/taxonomy/jppfs/2023/jppfs_cor">
  <link:schemaRef xlink:type="simple" xlink:href="jppfs_cor_2023.xsd"/>
  <context id="CurrentYearDuration">
    <entity>
      <identifier scheme="http://disclosure.edinet-fsa.go.jp">E12345</identifier>
    </entity>
    <period>
      <startDate>2023-04-01</startDate>
      <endDate>2024-03-31</endDate>
    </period>
  </context>
  <jppfs_cor:NetSales contextRef="CurrentYearDuration" unitRef="JPY" decimals="-6">1000000</jppfs_cor:NetSales>
  <jppfs_cor:OperatingIncome contextRef="CurrentYearDuration" unitRef="JPY" decimals="-6">50000</jppfs_cor:OperatingIncome>
</xbrl>"""

    zip_path = raw_dir / "edinet_type1.zip"
    with zipfile.ZipFile(zip_path, "w") as z:
        z.writestr("PublicDoc/test.xbrl", xbrl_content)

    print(f"Created dummy ZIP at {zip_path}")

    # 3. Insert DB Record
    db = SessionLocal()

    # Clean up old
    db.query(EdinetFile).filter_by(doc_id=doc_id).delete()
    db.query(EdinetXbrlFact).filter_by(doc_id=doc_id).delete()
    db.commit()

    ef = EdinetFile(
        doc_id=doc_id,
        file_type="ZIP_TYPE1",
        storage_path=str(zip_path.relative_to(BASE_STORAGE_DIR)),
        file_size=zip_path.stat().st_size,
        sha256="dummyhash",
        status="OK",
        downloaded_at=datetime.now(),
    )
    db.add(ef)
    db.commit()
    db.close()

    return doc_id


def verify_processor(doc_id):
    print(f"--- Running Verification for {doc_id} ---")
    db = SessionLocal()
    processor = XbrlProcessor(db=db)

    # Run
    result = processor.process_document(doc_id)
    print("Result JSON:", json.dumps(result, indent=2, ensure_ascii=False))

    # Verify Extracted Dir
    year = "2024"
    month = "01"
    extracted_dir = BASE_STORAGE_DIR / year / month / doc_id / "extracted" / "type1"
    if (extracted_dir / "PublicDoc/test.xbrl").exists():
        print("[PASS] Extraction successful")
    else:
        print("[FAIL] Extracted file missing")

    # Verify JSON Log
    json_log = BASE_STORAGE_DIR / year / month / doc_id / "derived" / "xbrl_detect.json"
    if json_log.exists():
        print("[PASS] JSON Log created")
    else:
        print("[FAIL] JSON Log missing")

    # Verify DB Facts
    facts = db.query(EdinetXbrlFact).filter_by(doc_id=doc_id).all()
    print(f"Facts found: {len(facts)}")
    for f in facts:
        print(
            f"  - {f.concept}: {f.value_numeric} (Text: {f.value_text}) Ctx: {f.context_ref}"
        )

    if len(facts) >= 2:
        print("[PASS] Facts extracted")
    else:
        print("[FAIL] Facts not extracted")

    db.close()


if __name__ == "__main__":
    doc_id = create_dummy_data()
    verify_processor(doc_id)
