import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

from database import SessionLocal
from models.edinet_document import EdinetDocument
from models.edinet_financial_highlight import EdinetFinancialHighlight
from models.edinet_derived import EdinetFinancialDerived

logger = logging.getLogger(__name__)


class DerivedMetricProcessor:
    def __init__(self, db: Session = None):
        self.db = db if db else SessionLocal()

    def process_document(self, doc_id: str):
        """
        Calculate derived metrics for a specific document.
        """
        # 1. Fetch Highlights
        highlights = (
            self.db.query(EdinetFinancialHighlight).filter_by(doc_id=doc_id).all()
        )
        if not highlights:
            logger.info(f"No highlights found for {doc_id}")
            return

        # 2. Index by metric_key
        # Note: Highlight Unique(doc_id, metric_key) guarantees one record per key per doc.
        metrics_map = {h.metric_key: h for h in highlights}

        # 3. Calculate each metric
        results = []

        # A. Margin (Duration / Duration)
        self._calc_margin(
            doc_id,
            metrics_map,
            "operating_margin",
            "operating_profit",
            "net_sales",
            "営業利益率",
        )
        self._calc_margin(
            doc_id,
            metrics_map,
            "net_margin",
            "profit_attributable_to_owners",
            "net_sales",
            "純利益率",
        )

        # B. Structure (Instant / Instant)
        self._calc_structure(
            doc_id,
            metrics_map,
            "equity_ratio",
            "equity",
            "total_assets",
            "自己資本比率",
        )

        # C. Return (Duration / Instant - Mixed Approx)
        self._calc_return(
            doc_id,
            metrics_map,
            "roe_end",
            "profit_attributable_to_owners",
            "equity",
            "ROE（期末近似）",
        )
        self._calc_return(
            doc_id,
            metrics_map,
            "roa_end",
            "profit_attributable_to_owners",
            "total_assets",
            "ROA（期末近似）",
        )

    def _calc_margin(self, doc_id, metrics_map, derived_key, num_key, den_key, label):
        """Calculate Margin (Duration / Duration)"""
        self._calculate_generic(
            doc_id,
            metrics_map,
            derived_key,
            label,
            num_key,
            den_key,
            rule_type="margin",
        )

    def _calc_structure(
        self, doc_id, metrics_map, derived_key, num_key, den_key, label
    ):
        """Calculate Structure (Instant / Instant)"""
        self._calculate_generic(
            doc_id,
            metrics_map,
            derived_key,
            label,
            num_key,
            den_key,
            rule_type="structure",
        )

    def _calc_return(self, doc_id, metrics_map, derived_key, num_key, den_key, label):
        """Calculate Return (Duration / Instant)"""
        self._calculate_generic(
            doc_id,
            metrics_map,
            derived_key,
            label,
            num_key,
            den_key,
            rule_type="return",
        )

    def _calculate_generic(
        self, doc_id, metrics_map, derived_key, label, num_key, den_key, rule_type
    ):
        num = metrics_map.get(num_key)
        den = metrics_map.get(den_key)

        # Basic Existence Check
        if not num or not den:
            # Skip if missing (Or Upsert NULL if we want to clear previous?)
            # User requirement: "計算しない" -> Skip might leave old data?
            # Better to verify idempotent behavior. Usually "process" implies refresh.
            # But if calculating batch, avoiding DB bloat with NULLs is preferred unless explicit delete needed.
            # For now, we skip saving anything if missing.
            return

        # Prepare Source Audit
        source_metrics = [num_key, den_key]
        source_values = {
            num_key: self._serialize_highlight(num),
            den_key: self._serialize_highlight(den),
        }
        formula = f"{num_key} / {den_key}"

        # Validation
        val_result = self._validate(num, den, rule_type)
        confidence = val_result["confidence"]
        reason = val_result["reason"]

        value = None
        period_type = None
        duration_days = None

        if val_result["valid"]:
            try:
                # Calculate
                # value_numeric in DB is Numeric (Decimal)
                n_val = num.value_numeric
                d_val = den.value_numeric

                if d_val and d_val != 0:
                    value = float(n_val) / float(d_val)
                else:
                    confidence = "LOW"
                    reason = "Division by zero"

                # Set metadata
                if rule_type == "margin":
                    period_type = num.period_type  # duration
                    duration_days = num.duration_days
                elif rule_type == "structure":
                    period_type = num.period_type  # instant
                    duration_days = None
                elif rule_type == "return":
                    period_type = "mixed_approx"
                    duration_days = num.duration_days  # Duration of numerator (Profit)

            except Exception as e:
                confidence = "LOW"
                reason = f"Calculation Error: {e}"
        else:
            # Invalid validation (Unit mismatch etc)
            # value remains None
            pass

        # DB Upsert
        self._upsert_derived(
            doc_id=doc_id,
            derived_key=derived_key,
            derived_label=label,
            value_numeric=value,
            period_type=period_type,
            duration_days=duration_days,
            source_metrics=source_metrics,
            source_values=source_values,
            calculation_formula=formula,
            confidence=confidence,
            reason=reason,
        )

    def _validate(self, num, den, rule_type) -> Dict:
        """
        Validate Unit and Period.
        """
        # 1. Unit Check
        # Must match textually AND contain "JPY" (Safety)
        u1 = num.unit_label or ""
        u2 = den.unit_label or ""

        if u1 != u2:
            return {
                "valid": False,
                "confidence": "LOW",
                "reason": f"Unit mismatch: {u1} vs {u2}",
            }

        if "JPY" not in u1 and "円" not in u1:
            # MVP restriction to JPY
            return {
                "valid": False,
                "confidence": "LOW",
                "reason": f"Non-JPY unit: {u1}",
            }

        # 2. Period Check
        p1 = num.period_type
        p2 = den.period_type

        if rule_type == "margin":
            # Duration / Duration
            if p1 != "duration" or p2 != "duration":
                return {
                    "valid": False,
                    "confidence": "LOW",
                    "reason": f"Period type mismatch for margin: {p1}/{p2}",
                }
            # Days Check
            d1 = num.duration_days
            d2 = den.duration_days
            if d1 != d2:
                return {
                    "valid": False,
                    "confidence": "LOW",
                    "reason": f"Duration days mismatch: {d1} vs {d2}",
                }

        elif rule_type == "structure":
            # Instant / Instant
            if p1 != "instant" or p2 != "instant":
                return {
                    "valid": False,
                    "confidence": "LOW",
                    "reason": f"Period type mismatch for structure: {p1}/{p2}",
                }

        elif rule_type == "return":
            # Duration / Instant
            if p1 != "duration" or p2 != "instant":
                return {
                    "valid": False,
                    "confidence": "LOW",
                    "reason": f"Period type mismatch for return: {p1}/{p2}",
                }
            if (
                "end" not in den.metric_key
                and "assets" not in den.metric_key
                and "equity" not in den.metric_key
            ):
                # Check if denominator is effectively 'end' (instant).
                # Edinet metric keys for instant are usually point in time.
                pass

        # 3. Source Confidence Check
        # If any source is LOW -> LOW
        if num.confidence == "MID" or den.confidence == "MID":
            conf = "MID"
        elif num.confidence == "LOW" or den.confidence == "LOW":
            conf = "LOW"
        else:
            conf = "HIGH"

        if rule_type == "return":
            # Return metrics are approx, max confidence is MID?
            # User requirement: "Return系（期末近似）は最大MID"
            if conf == "HIGH":
                conf = "MID"

        return {"valid": True, "confidence": conf, "reason": "OK"}

    def _serialize_highlight(self, obj):
        return {
            "value": (
                float(obj.value_numeric) if obj.value_numeric is not None else None
            ),
            "unit": obj.unit_label,
            "confidence": obj.confidence,
            "period": obj.period_type,
            "days": obj.duration_days,
        }

    def _upsert_derived(self, **kwargs):
        # Use simple merge for SQLite/Postgres generic support via ORM
        # ORM merge does SELECT then INSERT/UPDATE.
        # Since we have UNIQUE constraint on (doc_id, derived_key), merge works as UPSERT.

        try:
            obj = EdinetFinancialDerived(**kwargs)
            self.db.merge(obj)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(
                f"Upsert Error {kwargs['doc_id']}/{kwargs['derived_key']}: {e}"
            )

    def __del__(self):
        # self.db.close()
        pass
