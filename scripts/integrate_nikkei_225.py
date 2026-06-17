import sys
import os
import pandas as pd
from datetime import datetime
from sqlalchemy.orm import Session

# Add project root
sys.path.insert(0, ".")

from database import SessionLocal, engine
from models import stock, master, company_info, edinet_file
from services.edinet_service import EdinetClient
from services.sector_mapping import SectorMapper

# Ensure tables exist
# Note: In Phase 2, we might want to DROP tables to apply new schema.
# But this script is for integration/upsert.
# The reinit_db.py script should be run separately if schema change is needed.
# For now, we assume schema is compatible or updated.
company_info.Base.metadata.create_all(bind=engine)
edinet_file.Base.metadata.create_all(bind=engine)


def integrate_nikkei_data():
    db = SessionLocal()
    client = EdinetClient()

    print("--- Starting Nikkei 225 Integration ---")

    # 1. Fetch EDINET Code List
    csv_path = client.fetch_edinet_code_list()
    if not csv_path:
        print("Failed to fetch EDINET Code List. Using local sample.")
        csv_path = os.path.join(os.getcwd(), "data", "edinet_code_list_sample.csv")
        if not os.path.exists(csv_path):
            print(f"Sample CSV not found at {csv_path}")
            return

    print(f"Code List CSV: {csv_path}")

    try:
        # Load CSV (Try CP932 then UTF-8)
        try:
            df = pd.read_csv(csv_path, encoding="cp932", skiprows=1)
        except UnicodeDecodeError:
            print("CP932 failed, trying UTF-8...")
            df = pd.read_csv(
                csv_path, encoding="utf-8", skiprows=0
            )  # Removing skiprows=1 because my sample HAS header at line 1

        print(f"Loaded {len(df)} rows from Code List.")
        print(f"Columns: {df.columns.tolist()}")

    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    # 2. Define Sample Nikkei 225 List (Major 10)
    # Security Code (4 digits)
    sample_list = [
        "7203",  # Toyota
        "6758",  # Sony
        "9984",  # Softbank Group
        "8306",  # MUFG
        "8316",  # SMFG
        "9983",  # Fast Retailing
        "7974",  # Nintendo
        "8035",  # Tokyo Electron
        "6098",  # Recruit
        "4063",  # Shin-Etsu Chemical
    ]

    print(f"Processing {len(sample_list)} sample companies...")

    for code in sample_list:
        try:
            # Match in CSV
            # Convert "7203" -> 72030
            target_code_num = int(code) * 10
            row = df[df["証券コード"] == target_code_num]

            if row.empty:
                print(f"Code {code} not found in EDINET list.")
                continue

            data = row.iloc[0]
            edinet_code = data["ＥＤＩＮＥＴコード"]
            corporate_name = data["提出者名"]
            address = data["所在地"]
            capital_str = (
                str(data["資本金"]).replace(",", "")
                if not pd.isna(data["資本金"])
                else None
            )
            capital = (
                int(capital_str) if capital_str and capital_str.isdigit() else None
            )
            representative = data["代表者名"]
            industry_name = data["提出者業種"]
            settlement_date = data.get("決算日")  # e.g. "3月31日"

            # Upsert Sector (Using Mapper)
            sector_mapper = SectorMapper()
            internal_sector_name = sector_mapper.get_internal_sector_name(industry_name)

            sector = None
            if internal_sector_name:
                sector = (
                    db.query(company_info.Sector)
                    .filter_by(name=internal_sector_name)
                    .first()
                )
                if not sector:
                    sector = company_info.Sector(name=internal_sector_name)
                    db.add(sector)
                    db.commit()
                    db.refresh(sector)

            # Upsert StockMaster (Ensure exists)
            stock_master = db.query(master.StockMaster).filter_by(code=code).first()
            if not stock_master:
                stock_master = master.StockMaster(
                    code=code, name=corporate_name
                )  # Basic info
                db.add(stock_master)
                db.commit()

            # Upsert CompanyInfo
            info = db.query(company_info.CompanyInfo).filter_by(stock_code=code).first()
            if not info:
                info = company_info.CompanyInfo(stock_code=code)
                db.add(info)

            info.edinet_code = edinet_code
            info.corporate_name_ja = corporate_name
            info.address = address
            info.capital = capital
            info.representative = representative
            info.settlement_date = settlement_date  # Save settlement date
            info.sector_id = sector.id if sector else None
            # market_id left null for now or default

            db.commit()
            print(f"Updated {code}: {corporate_name} / E-Code: {edinet_code}")

        except Exception as e:
            print(f"Error processing {code}: {e}")
            db.rollback()

    db.close()
    print("--- Integration Complete ---")


if __name__ == "__main__":
    integrate_nikkei_data()
