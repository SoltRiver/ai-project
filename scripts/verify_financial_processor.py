
import sys
import datetime
import yaml
from sqlalchemy.orm import Session

# Add project root
sys.path.insert(0, ".")

from database import SessionLocal
from models.edinet_document import EdinetDocument
from models.edinet_xbrl_fact import EdinetXbrlFact
from models.edinet_financial_highlight import EdinetFinancialHighlight
from services.financial_processor import FinancialProcessor

def verify():
    # Debug YAML
    print("--- Debug: Loading Config ---")
    try:
        with open("config/edinet_metrics.yml", "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            print(data)
    except Exception as e:
        print(f"YAML Load Failed: {e}")

    db = SessionLocal()
    doc_id = "TEST_FIN"
    
    print(f"--- Setting up Dummy Data for {doc_id} ---")
    
    # 1. Ensure Doc Exists
    # Clean up first
    db.query(EdinetFinancialHighlight).filter_by(doc_id=doc_id).delete()
    db.query(EdinetXbrlFact).filter_by(doc_id=doc_id).delete()
    db.query(EdinetDocument).filter_by(doc_id=doc_id).delete()
    db.commit()
    
    doc = EdinetDocument(
        doc_id=doc_id,
        target_date=datetime.date(2024, 6, 25),
        filer_name="Test Corp"
    )
    db.add(doc)
    db.commit()
    
    # 2. Insert Facts
    # NetSales: Perfect Match
    f1 = EdinetXbrlFact(
        doc_id=doc_id,
        concept="jppfs_cor:NetSales",
        value_numeric=1234567,
        value_text="1,234,567",
        unit_ref="JPY",
        period_start=datetime.date(2023, 4, 1),
        period_end=datetime.date(2024, 3, 31) # 365 days
    )
    
    # OperatingProfit: Range Mismatch (Short duration)
    f2 = EdinetXbrlFact(
        doc_id=doc_id,
        concept="jppfs_cor:OperatingIncome",
        value_numeric=9999,
        value_text="9,999",
        unit_ref="JPY",
        period_start=datetime.date(2023, 4, 1),
        period_end=datetime.date(2023, 6, 30) # 90 days (Quarterly)
    )
    
    # OrdinaryProfit: No Numeric (Bad data)
    f3 = EdinetXbrlFact(
        doc_id=doc_id,
        concept="jppfs_cor:OrdinaryIncome",
        value_numeric=None,
        value_text="Renamed",
        period_start=datetime.date(2023, 4, 1),
        period_end=datetime.date(2024, 3, 31)
    )
    
    db.add_all([f1, f2, f3])
    db.commit()
    
    # 3. Run Processor
    print("--- Running Processor ---")
    processor = FinancialProcessor(db=db)
    logs = processor.process_document(doc_id)
    
    # 4. Verify
    print("--- Verification Results ---")
    highlights = db.query(EdinetFinancialHighlight).filter_by(doc_id=doc_id).all()
    
    h_map = {h.metric_key: h for h in highlights}
    
    # Check Net Sales (Expected HIGH)
    sales = h_map.get("net_sales")
    if sales:
        print(f"[NetSales] Conf: {sales.confidence}, Val: {sales.value_numeric}, Dur: {sales.duration_days}, Label: '{sales.metric_label}'")
        if sales.confidence == "HIGH" and sales.value_numeric == 1234567:
            print("  -> PASS")
        else:
            print("  -> FAIL (Expected HIGH, 1234567)")
    else:
        print("[NetSales] NOT FOUND -> FAIL")
        
    # Check Operating Profit (Expected MID or LOW depending on logic? Config says range 300-400)
    # 90 days is out of range. So should be MID (if numeric exists) or LOW.
    # Logic: "MID: ... Range NG but Numeric"
    op = h_map.get("operating_profit")
    if op:
        print(f"[OpProfit] Conf: {op.confidence}, Val: {op.value_numeric}, Dur: {op.duration_days}")
        if op.confidence == "MID":
            print("  -> PASS")
        else:
            print("  -> FAIL (Expected MID)")
    else:
        print("[OpProfit] NOT FOUND -> FAIL")

    # Check Ordinary Profit (Expected LOW - No numeric)
    # Logic: "LOW: No numeric OR No concept"
    ord_p = h_map.get("ordinary_profit")
    if ord_p:
        print(f"[OrdProfit] Conf: {ord_p.confidence}, Val: {ord_p.value_numeric}")
        if ord_p.confidence == "LOW" and ord_p.value_numeric is None:
            print("  -> PASS")
        else:
            print("  -> FAIL (Expected LOW, None)")
    else:
        print("[OrdProfit] NOT FOUND -> FAIL (Should insert record with LOW?)")
        # Logic says upsert occurs even if LOW.

    # Check Net Income (Not in facts)
    # Should be present with CONFIDENCE=LOW, Reason=Concept not found
    ni = h_map.get("net_income")
    if ni:
        print(f"[NetIncome] Conf: {ni.confidence}, Reason: {ni.reason}")
        if ni.confidence == "LOW" and "concept not found" in ni.reason:
            print("  -> PASS")
        else:
            print("  -> FAIL")
    else:
        print("[NetIncome] NOT FOUND -> FAIL")

    db.close()

if __name__ == "__main__":
    verify()
