import sys
import os

sys.path.insert(0, ".")
import asyncio
import logging

# Re-configure logging to show everything
logging.basicConfig(level=logging.DEBUG)


def log(msg):
    print(msg, flush=True)


async def run(doc_id):
    log(f"--- STARTING DEBUG FOR {doc_id} ---")

    from services.edinet_document_store import EdinetDocumentStore

    store = EdinetDocumentStore()
    log("Store initialized.")

    try:
        log("Extracting document...")
        unzipped_dir = store.extract_document(doc_id)
        log(f"Extracted to: {unzipped_dir}")
    except Exception as e:
        log(f"Extraction failed: {e}")
        return

    from services.edinet_xbrl_locator import EdinetXbrlLocator

    locator = EdinetXbrlLocator()
    log("Locator initialized.")

    log("Locating XBRL...")
    location_result = await locator.locate_xbrl_files(unzipped_dir)
    primary_xbrl = location_result.get("primary_xbrl")
    log(f"Primary XBRL path: {primary_xbrl}")

    if not primary_xbrl:
        log("No primary XBRL found.")
        return

    from services.edinet_fin_extract import EdinetFinancialExtractor

    extractor = EdinetFinancialExtractor()
    log("Extractor initialized.")

    log("Calling extract_financials...")
    try:
        financials = extractor.extract_financials(primary_xbrl)
        log("Extraction returned.")
    except Exception as e:
        log(f"Extraction crashed: {e}")
        import traceback

        traceback.print_exc()
        return

    log("--- Financials Content ---")
    for k, v in financials.items():
        if k.startswith("dividend"):
            log(f"{k}: {v}")

    log("--- DONE ---")


if __name__ == "__main__":
    doc_id = "S100TR7I"
    if len(sys.argv) > 1:
        doc_id = sys.argv[1]
    asyncio.run(run(doc_id))
