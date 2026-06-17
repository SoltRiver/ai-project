from __future__ import annotations

import json
import logging
import os
from datetime import datetime, date
from typing import List, Dict, Optional, Any

from sqlalchemy.orm import Session
from sqlalchemy import or_

from database import SessionLocal
from models.master import StockMaster, AppSyncStatus
from data.stock_name_mapper import (
    STOCK_NAME_MAP,
)  # Keep as fallback if needed, but main source is DB

# J-Quants Client (will be updated to support get_listed_issues)
from services.jquants_client import client as jquants_client

logger = logging.getLogger(__name__)

SEED_FILE_PATH = os.path.join("data", "seed_stock_master.json")


class StockMasterService:
    def __init__(self):
        pass

    def get_db(self):
        return SessionLocal()

    # --- Repository Methods ---

    def search_stocks(self, query: str, limit: int = 10) -> List[Dict[str, str]]:
        """
        Search stocks in local DB by code or name.
        Returns list of dicts: {"code": ..., "name": ...}
        """
        query = query.strip()
        if not query:
            return []

        db = self.get_db()
        try:
            # Prefix search or partial match
            # "7203" -> match code
            # "Toyota" -> match name
            # Using ILIKE for case-insensitive if supported, but SQLite matches case-insensitive for ASCII usually.
            # For Japanese characters, consistency depends on collation.

            # Simple LIKE query
            wildcard = f"{query}%"  # Prefix match preferred
            wildcard_contain = f"%{query}%"

            # Prioritize code prefix match first?
            # Or just simple OR condition.

            results = (
                db.query(StockMaster)
                .filter(
                    or_(
                        StockMaster.code.like(wildcard),
                        StockMaster.name.like(wildcard_contain),
                    )
                )
                .order_by(StockMaster.code)
                .limit(limit)
                .all()
            )

            return [{"code": r.code, "name": r.name} for r in results]

        finally:
            db.close()

    def upsert_stocks(self, items: List[Dict[str, Any]], source: str):
        """
        Bulk upsert stock master items.
        items: list of dict {"code": str, "name": str, "market": str}
        """
        if not items:
            return

        db = self.get_db()
        try:
            # SQLite doesn't have good bulk UPSERT support in generic SQLAlchemy without dialects.
            # Simple approach: Merge one by one. Or delete all and re-insert?
            # Re-inserting is risky if we have foreign keys (currently none).
            # Merge is safest.

            # Optimization: Fetch existing codes to decide insert vs update?
            # Only 4000 stocks, merge is acceptable speed.

            count = 0
            for item in items:
                code = str(item["code"])
                name = item["name"]
                market = item.get("market", "")

                # Check exist
                stock = db.query(StockMaster).get(code)
                if stock:
                    stock.name = name
                    stock.market = market
                    # updated_at will auto update
                else:
                    stock = StockMaster(code=code, name=name, market=market)
                    db.add(stock)

                count += 1
                if count % 100 == 0:
                    db.commit()

            db.commit()
            logger.info(f"Upserted {count} stocks from {source}")

            # Update Sync Status
            self._update_sync_status(db, "SUCCESS", None, source)

        except Exception as e:
            logger.error(f"Failed to upsert stocks: {e}")
            db.rollback()
            self._update_sync_status(db, "FAILED", str(e), source)
        finally:
            db.close()

    def _update_sync_status(
        self, db: Session, status: str, error: Optional[str], source: str
    ):
        try:
            # Single row table
            sync_status = db.query(AppSyncStatus).get(1)
            if not sync_status:
                sync_status = AppSyncStatus(id=1)
                db.add(sync_status)

            sync_status.last_synced_at = datetime.now()
            sync_status.last_sync_status = status
            sync_status.last_sync_error = error
            sync_status.source = source
            db.commit()
        except Exception as e:
            logger.error(f"Failed to update sync status: {e}")

    # --- Sync Logic ---

    def initialize_and_sync(self):
        """
        Main entry point for startup.
        1. Ensure DB has data (Seed).
        2. Sync from J-Quants if stale.
        """
        logger.info("Initializing Stock Master...")

        try:
            self._ensure_seed_if_empty()
            self._sync_from_jquants_if_needed()
        except Exception as e:
            # Catch-all to prevent app crash
            logger.error(f"Critical error during Stock Master initialization: {e}")

    def _ensure_seed_if_empty(self):
        db = self.get_db()
        try:
            count = db.query(StockMaster).count()
            if count == 0:
                logger.info("Stock Master is empty. Loading seed data...")
                if os.path.exists(SEED_FILE_PATH):
                    with open(SEED_FILE_PATH, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        # data is list of dicts
                        # Close DB session before calling upsert (it opens its own)
                        db.close()
                        self.upsert_stocks(data, "seed")
                        return
                else:
                    logger.warning(f"Seed file not found at {SEED_FILE_PATH}")
            else:
                logger.info(f"Stock Master has {count} records. Skipping seed.")
        finally:
            # Ensure closed if not returned early
            if db.is_active:
                db.close()

    def _sync_from_jquants_if_needed(self):
        """
        Check sync status and sync from J-Quants if necessary.
        Policy: Sync once per day.
        """
        db = self.get_db()
        try:
            sync_status = db.query(AppSyncStatus).get(1)
            should_sync = True

            if sync_status and sync_status.last_synced_at:
                last_date = sync_status.last_synced_at.date()
                today = date.today()
                if last_date == today and sync_status.last_sync_status == "SUCCESS":
                    should_sync = False

            if should_sync:
                logger.info("Starting J-Quants Sync...")
                db.close()  # Release for upsert
                self._sync_from_jquants()
            else:
                logger.info("Stock Master is up-to-date. Skipping J-Quants sync.")

        finally:
            if db.is_active:
                db.close()

    def _sync_from_jquants(self):
        try:
            # 1. Fetch from API
            # This method needs to be implemented in JQuantsClient
            raw_issues = (
                jquants_client.get_listed_issues()
            )  # Returns list of issue dicts

            if not raw_issues:
                logger.warning("J-Quants returned empty list. Skipping update.")
                return

            # 2. Normalize
            items = []
            for issue in raw_issues:
                # V2: "Code": "72030" -> "7203"
                raw_code = issue.get("Code", "")
                if len(raw_code) == 5 and raw_code.endswith("0"):
                    code = raw_code[:4]
                else:
                    code = raw_code

                # V2 Mapping
                # CoName -> CompanyName
                # MktNm -> MarketName/Segment
                name = issue.get("CoName", "") or issue.get("CompanyName", "")
                market = issue.get("MktNm", "") or issue.get("MarketCodeName", "")

                if code and name:
                    items.append({"code": code, "name": name, "market": market})

            # 3. Upsert
            if items:
                self.upsert_stocks(items, "jquants_v2")

        except Exception as e:
            logger.error(f"J-Quants Sync Failed: {e}")
            # Log failure to DB
            db = self.get_db()
            self._update_sync_status(db, "FAILED", str(e), "jquants")
            db.close()


# Singleton
stock_master_service = StockMasterService()
