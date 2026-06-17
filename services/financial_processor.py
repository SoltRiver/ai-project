import logging
import yaml
from pathlib import Path
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text  # For raw sql or complex upsert if needed
from sqlalchemy.dialects.postgresql import insert as pg_insert

from database import SessionLocal
from models.edinet_xbrl_fact import EdinetXbrlFact
from models.edinet_financial_highlight import EdinetFinancialHighlight

logger = logging.getLogger(__name__)


class FinancialProcessor:
    def __init__(
        self, db: Session = None, config_path: str = "config/edinet_metrics.yml"
    ):
        self.db = db if db else SessionLocal()
        self.config = self._load_config(config_path)

    def _load_config(self, path: str) -> Dict:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load config {path}: {e}")
            return {"metrics": []}

    def process_document(self, doc_id: str):
        """
        Process a single document: Extract highlights based on config.
        """
        print(f"Processing Highlights for {doc_id}...")

        metrics_def = self.config.get("metrics", [])

        # Pre-fetch all facts for this doc to avoid N+1
        # We need concept, period, value etc.
        # Store in memory map? Or just query per metric?
        # Query per metric is safer for complex filtering, but slower.
        # "doc_id単位で該当factを一括取得し、アプリ側でフィルタリングする" -> Bulk fetch recommended.

        all_facts = self.db.query(EdinetXbrlFact).filter_by(doc_id=doc_id).all()
        # Index facts by concept for speed?
        # A concept might have multiple facts (diff contexts).
        facts_by_concept = {}
        for f in all_facts:
            if f.concept not in facts_by_concept:
                facts_by_concept[f.concept] = []
            facts_by_concept[f.concept].append(f)

        results = []
        logs = []

        for metric in metrics_def:
            key = metric["metric_key"]
            label = metric["metric_label"]
            candidates = metric["concept_candidates"]
            duration_range = metric.get("prefer_duration_days_range")

            # Find best fact
            best_fact = None
            best_score = -1  # 0=Low, 1=Mid, 2=High
            confidence = "LOW"
            reason = "concept not found"

            found_candidate_facts = []

            # 1. Search candidates in order
            for priority, concept in enumerate(candidates):
                facts = facts_by_concept.get(concept, [])
                if not facts:
                    continue

                # Check each fact
                for f in facts:
                    # Calc duration
                    duration = self._calc_duration(f)

                    # Logic 3-3: Value Check
                    # "value_numeric" is preferred, but text is essential fallback.
                    # Safety: MVP req says "value_numericが取得できる" for High priority.
                    has_val = f.value_numeric is not None

                    # Score Calculation
                    # Priority 1: Concept matches (priority index 0 is best)
                    # Priority 2: Duration in range
                    # Priority 3: Value numeric exists

                    # Creating a score tuple? (concept_prio, duration_ok, value_ok, period_end)
                    # Lower concept_prio is better.

                    is_duration_ok = False
                    if duration is not None and duration_range:
                        if duration_range[0] <= duration <= duration_range[1]:
                            is_duration_ok = True

                    # Determine Confidence
                    # HIGH: 1st candidate + Range OK + Numeric
                    # MID: 2nd+ candidate OR Range NG but Numeric
                    # LOW: No numeric OR No concept

                    curr_conf = "LOW"
                    curr_reason = ""

                    if priority == 0 and is_duration_ok and has_val:
                        curr_conf = "HIGH"
                        curr_reason = f"Primary matched, duration {duration}"
                        score = 100
                    elif has_val and (priority > 0 or not is_duration_ok):
                        curr_conf = "MID"
                        reason_parts = []
                        if priority > 0:
                            reason_parts.append(f"Fallback {concept}")
                        if not is_duration_ok:
                            reason_parts.append(f"Duration {duration} mismatch")
                        curr_reason = ", ".join(reason_parts)
                        score = 50 - priority  # Fallback priority lowers score
                    else:
                        curr_conf = "LOW"
                        curr_reason = "No numeric value"
                        score = 10

                    # Tie breaker: Period End (Latest is best)
                    # We add period_end timestamp to score?
                    # Or just keep best.

                    if score > best_score:
                        best_score = score
                        best_fact = f
                        confidence = curr_conf
                        reason = curr_reason
                    elif score == best_score:
                        # Compare period_end
                        if f.period_end and best_fact.period_end:
                            if f.period_end > best_fact.period_end:
                                best_fact = f
                                confidence = curr_conf
                                reason = curr_reason

            # If no fact found at all
            if not best_fact:
                logs.append(
                    {
                        "doc_id": doc_id,
                        "metric_key": key,
                        "candidates": candidates,
                        "result": "NOT_FOUND",
                        "confidence": "LOW",
                        "duration": None,
                    }
                )
                # Even if not found, we might want to insert a "Missing" record?
                # User says: "該当なしの場合... confidence=LOW, reason='concept not found'... レポート対象"
                # And "誤判定よりも...unknownを許容"
                # Should we upsert a NULL record?
                # "scopeや期間の無理な推定はしない"
                # "value_numeric=NULL... レポート対象とする（後述）"
                # Report logic is in Section 5.
                # Section 1 DDL has NOT NULL on metric_key/label.
                # So we CAN insert a record with null values.

                # Let's insert the "Not Found" record to track it in DB?
                results.append(
                    {
                        "metric_key": key,
                        "metric_label": label,
                        "selected_fact_id": None,
                        "scope": "unknown",
                        "period_type": "unknown",
                        "duration_days": None,
                        "period_start": None,
                        "period_end": None,
                        "value_numeric": None,
                        "raw_value_text": None,
                        "unit_label": None,
                        "source_concept": None,
                        "confidence": "LOW",
                        "reason": "concept not found",
                    }
                )

            else:
                # Found
                dur = self._calc_duration(best_fact)
                p_type = (
                    "duration"
                    if dur is not None
                    else ("instant" if best_fact.instant_date else "unknown")
                )
                scope = "unknown"  # MVP fixed

                results.append(
                    {
                        "metric_key": key,
                        "metric_label": label,
                        "selected_fact_id": best_fact.id,
                        "scope": scope,
                        "period_type": p_type,
                        "duration_days": dur,
                        "period_start": best_fact.period_start,
                        "period_end": best_fact.period_end
                        or best_fact.instant_date,  # Use instant as end?
                        "value_numeric": best_fact.value_numeric,
                        "raw_value_text": best_fact.value_text,
                        "unit_label": best_fact.unit_ref,
                        "source_concept": best_fact.concept,
                        "confidence": confidence,
                        "reason": reason,
                    }
                )

                logs.append(
                    {
                        "doc_id": doc_id,
                        "metric_key": key,
                        "candidates": candidates,
                        "result": "FOUND",
                        "confidence": confidence,
                        "duration": dur,
                    }
                )

        # Bulk Upsert
        self._upsert_highlights(doc_id, results)

        # Output Logs
        for l in logs:
            if l["result"] == "NOT_FOUND":
                print(
                    f"[WARN] Missing {l['metric_key']} in {doc_id}. Conf: {l['confidence']}"
                )
            else:
                # Optional info log
                pass

        return logs

    def _calc_duration(self, fact: EdinetXbrlFact) -> Optional[int]:
        if fact.period_start and fact.period_end:
            delta = fact.period_end - fact.period_start
            return delta.days
        return None

    def _upsert_highlights(self, doc_id: str, data: List[Dict]):
        # SQLite doesn't support "ON CONFLICT ... UPDATE" with standard insert() easily without dialect specific
        # But we are mocking Postgres behavior?
        # User requirement says "UPSERT (冪等)"
        # "INSERT ... ON CONFLICT (doc_id, metric_key) DO UPDATE SET ..."

        # For pure SQLAlchemy generic support, we often use merge() or dialect specific.
        # Since we run on SQLite for now (dev) but target Postgres (DDL),
        # we can simulate upsert by "Check Exist -> Update or Insert".

        for item in data:
            # Check
            existing = (
                self.db.query(EdinetFinancialHighlight)
                .filter_by(doc_id=doc_id, metric_key=item["metric_key"])
                .first()
            )

            if existing:
                # Update
                existing.selected_fact_id = item["selected_fact_id"]
                existing.scope = item["scope"]
                existing.period_type = item["period_type"]
                existing.duration_days = item["duration_days"]
                existing.period_start = item["period_start"]
                existing.period_end = item["period_end"]
                existing.value_numeric = item["value_numeric"]
                existing.raw_value_text = item["raw_value_text"]
                existing.unit_label = item["unit_label"]
                existing.source_concept = item["source_concept"]
                existing.confidence = item["confidence"]
                existing.reason = item["reason"]
                existing.updated_at = datetime.now()
            else:
                # Insert
                # Debug
                # Print item keys and metric_label specifically
                print(
                    f"[DEBUG] Inserting: key={item.get('metric_key')}, label={item.get('metric_label')}"
                )

                if "metric_label" not in item or item["metric_label"] is None:
                    print(f"[ERROR] metric_label IS NONE OR MISSING: {item}")

                new_rec = EdinetFinancialHighlight(doc_id=doc_id, **item)
                self.db.add(new_rec)

        try:
            self.db.commit()
        except Exception as e:
            print(f"[DB ERROR] Commit failed: {e}")
            self.db.rollback()
            raise e

    def __del__(self):
        pass  # self.db.close() handled by caller usually
