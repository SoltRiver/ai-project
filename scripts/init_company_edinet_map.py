"""
CompanyInfo 初期データ構築スクリプト

シード銘柄30社の CompanyInfo レコードを edinet_batch_config.yml の
seed_edinet_map を使用して作成する。
既存レコードがある場合はスキップする（冪等）。

使用方法:
    python scripts/init_company_edinet_map.py
"""

import sys
import os
import yaml

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from database import SessionLocal, engine, Base
from models.master import StockMaster
from models.company_info import CompanyInfo, Sector, Market
from models.edinet_batch_log import EdinetBatchLog


def load_config() -> dict:
    """バッチ設定ファイルを読み込む"""
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "config",
        "edinet_batch_config.yml",
    )
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def init_company_edinet_map():
    """シード銘柄の CompanyInfo を初期作成"""
    config = load_config()
    seed_map = config.get("seed_edinet_map", {})

    if not seed_map:
        print("ERROR: seed_edinet_map が設定ファイルに見つかりません")
        return

    # テーブルが存在しない場合は作成
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        created = 0
        skipped = 0
        updated = 0

        for stock_code, edinet_code in seed_map.items():
            # StockMaster の存在確認
            master = (
                db.query(StockMaster).filter(StockMaster.code == stock_code).first()
            )

            if not master:
                print(f"  WARN: StockMaster に {stock_code} が存在しません。スキップ")
                skipped += 1
                continue

            # CompanyInfo の既存チェック
            existing = (
                db.query(CompanyInfo)
                .filter(CompanyInfo.stock_code == stock_code)
                .first()
            )

            if existing:
                # edinet_code が未設定なら更新
                if not existing.edinet_code:
                    existing.edinet_code = edinet_code
                    updated += 1
                    print(
                        f"  UPDATE: {stock_code} ({master.name}) edinet_code={edinet_code}"
                    )
                else:
                    skipped += 1
                    print(
                        f"  SKIP: {stock_code} ({master.name}) 既に edinet_code={existing.edinet_code}"
                    )
                continue

            # 新規作成
            new_company = CompanyInfo(
                stock_code=stock_code,
                edinet_code=edinet_code,
                corporate_name_ja=master.name,
            )
            db.add(new_company)
            created += 1
            print(f"  CREATE: {stock_code} ({master.name}) edinet_code={edinet_code}")

        db.commit()
        print(f"\n--- 完了 ---")
        print(f"  作成: {created}件")
        print(f"  更新: {updated}件")
        print(f"  スキップ: {skipped}件")

    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("=== CompanyInfo 初期データ構築 ===\n")
    init_company_edinet_map()
