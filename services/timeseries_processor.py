import logging
import math
from datetime import date
from typing import List, Dict, Optional, Tuple
from sqlalchemy import text, func, and_
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

from database import SessionLocal
from models.edinet_document import EdinetDocument
from models.edinet_financial_highlight import EdinetFinancialHighlight
from models.edinet_timeseries import EdinetMetricTimeseries, EdinetMetricComparison

logger = logging.getLogger(__name__)

# Metric Rules (YAML-like config in code)
METRIC_RULES = {
    "net_sales": {"expected_period": "duration"},
    "operating_profit": {"expected_period": "duration"},
    "ordinary_profit": {"expected_period": "duration"},
    "profit_attributable_to_owners": {"expected_period": "duration"},
    "total_assets": {"expected_period": "instant"},
    "equity": {"expected_period": "instant"},
}

ANNUAL_DAYS_MIN = 300
ANNUAL_DAYS_MAX = 400


class TimeseriesProcessor:
    def __init__(self, db: Session = None):
        self.db = db if db else SessionLocal()

    def process_sec_code(self, sec_code: str):
        """
        Process timeseries and comparisons for a single sec_code.
        """
        logger.info(f"Processing Timeseries for {sec_code}...")

        # 1. Select Annual Docs
        year_doc_map = self._select_annual_docs(sec_code)
        if not year_doc_map:
            logger.info(f"No annual docs found for {sec_code}")
            return

        # 2. Extract Timeseries (TimeseriesPopulator)
        self._populate_timeseries(sec_code, year_doc_map)

        # 3. Calculate Comparison (ComparisonCalculator)
        self._calculate_comparisons(sec_code)

    def _select_annual_docs(self, sec_code: str) -> Dict[int, EdinetDocument]:
        """
        Select representative doc for each fiscal year.
        Rule: Annual Duration (300-400), Priority (Report > Amendment), Latest Submit.
        """
        # Fetch all candidate docs
        # Join with Highlights or rely on Doc metadata?
        # Since we need duration_days, and that is in Highlight, we might need a join or just fetch docs and query highlights later.
        # Efficient approach: Fetch docs, then filter by Highlight duration check.

        docs = (
            self.db.query(EdinetDocument)
            .filter(
                EdinetDocument.sec_code == sec_code, EdinetDocument.period_end != None
            )
            .order_by(EdinetDocument.period_end)
            .all()
        )

        candidates_by_year = {}

        for doc in docs:
            # Check duration via Highlight?
            # Or assume period_end - period_start?
            # EdinetDocument has period_start/end. Let's use that for fast filtering.
            if not doc.period_start or not doc.period_end:
                continue

            delta = (doc.period_end - doc.period_start).days
            if not (ANNUAL_DAYS_MIN <= delta <= ANNUAL_DAYS_MAX):
                continue

            year = doc.period_end.year
            if year not in candidates_by_year:
                candidates_by_year[year] = []

            candidates_by_year[year].append(doc)

        # Select Best
        selected_map = {}
        for year, year_docs in candidates_by_year.items():
            # Sort: Priority (Report vs Amendment) -> SubmitDate (Desc)
            # doc_description usually contains "有価証券報告書" or "訂正"

            # Sort key logic:
            # 1. Doc Type Priority: Report (High) > Amendment (Low) ?
            # User says: USE_AMENDED=false (MVP default?).
            # User says: "USE_AMENDED = false" in requirement 2.
            # But "priority: Report, (if USE_AMENDED=true) Amendment".
            # If USE_AMENDED is false, we ignore amendments?
            # Let's implementation: Filter out "訂正" if USE_AMENDED=False (default).

            # Assuming "有価証券報告書" (120) is the main one.
            # "訂正有価証券報告書" is diff code or desc.

            filtered_docs = []
            for d in year_docs:
                desc = d.doc_description or ""
                if "有価証券報告書" in desc and "訂正" not in desc:
                    filtered_docs.append(d)
                # If we were to support amended, we would look for "訂正" here

            if not filtered_docs:
                continue

            # If multiple, take latest submit_datetime
            # Python sort is stable, desc date
            filtered_docs.sort(
                key=lambda x: x.submit_datetime or x.created_at, reverse=True
            )

            best_doc = filtered_docs[0]
            selected_map[year] = best_doc

            # Audit note creation (deferred to insert)

        return selected_map

    def _populate_timeseries(
        self, sec_code: str, year_doc_map: Dict[int, EdinetDocument]
    ):
        for year, doc in year_doc_map.items():
            # Fetch highlights
            highlights = (
                self.db.query(EdinetFinancialHighlight)
                .filter_by(doc_id=doc.doc_id)
                .all()
            )

            for h in highlights:
                # Type Check
                rule = METRIC_RULES.get(h.metric_key)
                if not rule:
                    continue  # Skip unknown metrics

                if h.period_type != rule["expected_period"]:
                    continue  # Period mismatch

                # Insert Timeseries
                audit_json = {
                    "rule": "Selected best annual doc",
                    "candidates_count": 1,  # Simplified audit
                    "doc_submit_date": str(doc.submit_datetime),
                }

                self._upsert_timeseries(
                    sec_code=sec_code,
                    metric_key=h.metric_key,
                    period_end_year=year,
                    fiscal_year_label=str(year),
                    doc_id=doc.doc_id,
                    value_numeric=h.value_numeric,
                    period_type=h.period_type,
                    duration_days=h.duration_days,
                    selection_notes=audit_json,
                )

    def _calculate_comparisons(self, sec_code: str):
        # Fetch all timeseries for this sec
        series = (
            self.db.query(EdinetMetricTimeseries)
            .filter_by(sec_code=sec_code)
            .order_by(
                EdinetMetricTimeseries.metric_key,
                EdinetMetricTimeseries.period_end_year,
            )
            .all()
        )

        # Group by metric
        grouped = {}
        for s in series:
            if s.metric_key not in grouped:
                grouped[s.metric_key] = []
            grouped[s.metric_key].append(s)

        for key, rows in grouped.items():
            # Rows are sorted by year
            history_vals = {}  # year -> val
            history_rows = {}  # year -> row obj
            for r in rows:
                history_vals[r.period_end_year] = (
                    float(r.value_numeric) if r.value_numeric is not None else None
                )
                history_rows[r.period_end_year] = r

            for i, curr in enumerate(rows):
                year = curr.period_end_year
                val = (
                    float(curr.value_numeric)
                    if curr.value_numeric is not None
                    else None
                )

                # Setup
                yoy_abs = None
                yoy_pct = None
                turnaround = None

                # YoY
                prev_year = year - 1
                prev_val = history_vals.get(prev_year)

                calc_notes = {}
                source_docs = []

                if prev_year in history_rows:
                    source_docs.append(history_rows[prev_year].doc_id)

                if val is not None and prev_val is not None:
                    yoy_abs = val - prev_val

                    if prev_val > 0:
                        yoy_pct = yoy_abs / prev_val
                    elif prev_val < 0 and val > 0:
                        turnaround = "NEG_TO_POS"
                    elif prev_val > 0 and val < 0:
                        turnaround = "POS_TO_NEG"
                    elif prev_val == 0:
                        calc_notes["prev_zero"] = True
                    else:
                        # prev < 0 and val < 0
                        calc_notes["neg_continuity"] = True

                else:
                    calc_notes["missing_prev"] = True

                # CAGR (3y)
                cagr3 = self._calc_cagr(history_vals, year, 3)
                cagr5 = self._calc_cagr(history_vals, year, 5)

                # Trend (5y)
                trend_res = self._calc_trend(history_vals, year, 5)

                # Upsert Comparison
                self._upsert_comparison(
                    sec_code=sec_code,
                    metric_key=key,
                    period_end_year=year,
                    doc_id=curr.doc_id,
                    yoy_abs=yoy_abs,
                    yoy_pct=yoy_pct,
                    turnaround_flag=turnaround,
                    cagr_3y=cagr3,
                    cagr_5y=cagr5,
                    trend_label=trend_res["label"],
                    trend_reason=trend_res["reason"],
                    source_docs=source_docs,
                    calc_notes=calc_notes,
                )

    def _calc_cagr(self, history, current_year, years):
        start_year = current_year - years
        start_val = history.get(start_year)
        curr_val = history.get(current_year)

        # Check continuity? MVP: just start and end existence
        if start_val and curr_val and start_val > 0 and curr_val > 0:
            try:
                return (curr_val / start_val) ** (1 / years) - 1
            except:
                return None
        return None

    def _calc_trend(self, history, current_year, years):
        # Get last N yoy_pct
        # Note: simplistic trend logic as requested
        # Positive count > 70% -> UP
        # Negative count > 70% -> DOWN

        # We need to calculate yoy for past years on the fly or fetch them?
        # Let's calculate from history vals

        yoy_list = []
        for i in range(years):
            # i=0 -> current (curr vs curr-1)
            # i=1 -> curr-1 vs curr-2
            y = current_year - i
            py = y - 1

            v = history.get(y)
            pv = history.get(py)

            if v and pv and pv > 0:
                pct = (v - pv) / pv
                if abs(pct) < 5.0:  # Extreme threshold
                    yoy_list.append(pct)

        if not yoy_list:
            return {"label": "UNKNOWN", "reason": "No data"}

        pos_count = sum(1 for x in yoy_list if x > 0)
        neg_count = sum(1 for x in yoy_list if x < 0)
        total = len(yoy_list)

        if total < 3:
            return {"label": "VOLATILE", "reason": "Insufficient data"}

        if pos_count / total >= 0.7:
            return {"label": "UP", "reason": f"{pos_count}/{total} positive"}
        if neg_count / total >= 0.7:
            return {"label": "DOWN", "reason": f"{neg_count}/{total} negative"}

        return {"label": "FLAT/VOLATILE", "reason": "Mixed"}

    def _upsert_timeseries(self, **kwargs):
        try:
            existing = (
                self.db.query(EdinetMetricTimeseries)
                .filter_by(
                    sec_code=kwargs["sec_code"],
                    metric_key=kwargs["metric_key"],
                    period_end_year=kwargs["period_end_year"],
                )
                .first()
            )

            if existing:
                for k, v in kwargs.items():
                    setattr(existing, k, v)
            else:
                self.db.add(EdinetMetricTimeseries(**kwargs))

            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Err TS: {e}")

    def _upsert_comparison(self, **kwargs):
        try:
            existing = (
                self.db.query(EdinetMetricComparison)
                .filter_by(
                    sec_code=kwargs["sec_code"],
                    metric_key=kwargs["metric_key"],
                    period_end_year=kwargs["period_end_year"],
                )
                .first()
            )

            if existing:
                for k, v in kwargs.items():
                    setattr(existing, k, v)
            else:
                self.db.add(EdinetMetricComparison(**kwargs))

            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Err Comp: {e}")

    def __del__(self):
        # self.db.close()
        pass
