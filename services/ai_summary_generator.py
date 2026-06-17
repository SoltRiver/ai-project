import logging
import hashlib
import json
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy import text, desc, func
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

from database import SessionLocal
from models.edinet_timeseries import EdinetMetricTimeseries, EdinetMetricComparison
from models.edinet_ai_summary import EdinetAISummary
from models.edinet_pdf import EdinetPdfText

logger = logging.getLogger(__name__)

# Keywords for PDF Evidence Search
PDF_KEYWORDS = ["減損", "下方修正", "営業損失", "債務超過", "継続企業の前提"]


class AISummaryGenerator:
    def __init__(self, db: Session = None):
        self.db = db if db else SessionLocal()

    def generate_for_sec_code(self, sec_code: str):
        """
        Generate AI Summary (Snapshot & Delta) for the LATEST valid year of the given sec_code.
        """
        # 1. Determine Reference Year & Doc
        ref = self._determine_reference(sec_code)
        if not ref:
            logger.info(f"No valid reference year found for {sec_code}")
            return

        base_year = ref["year"]
        base_doc_id = ref["doc_id"]

        # 2. Build Facts
        facts = self._build_facts(sec_code, base_year, base_doc_id)

        # 3. Canonicalize & Hash
        input_hash = self._compute_hash(facts)

        # 4. Check Existing
        existing = (
            self.db.query(EdinetAISummary)
            .filter_by(
                sec_code=sec_code,
                period_end_year=base_year,
                kind="SNAPSHOT",  # We store both in one, or separate?
                # Schema says 'kind'. User requested SNAPSHOT and DELTA summaries.
                # Usually these are displayed together.
                # Let's generate both using the same facts/hash.
            )
            .first()
        )

        if existing and existing.input_hash == input_hash:
            logger.info(f"Skipping {sec_code} {base_year}: Hash match")
            return

        # 5. Generate Texts
        snapshot_text, snapshot_bullets = self._generate_snapshot_text(facts)
        delta_text, delta_bullets = self._generate_delta_text(facts)

        # 6. Upsert
        self._upsert_summary(
            sec_code,
            base_year,
            "SNAPSHOT",
            snapshot_text,
            snapshot_bullets,
            facts,
            input_hash,
        )
        self._upsert_summary(
            sec_code, base_year, "DELTA", delta_text, delta_bullets, facts, input_hash
        )

        logger.info(f"Generated Summary for {sec_code} {base_year}")

    def _determine_reference(self, sec_code: str) -> Optional[Dict]:
        """
        Priority:
        1. Latest year with net_sales
        2. Latest with profit_attributable_to_owners
        3. Latest with operating_profit
        4. Latest available
        """
        priorities = ["net_sales", "profit_attributable_to_owners", "operating_profit"]

        for metric in priorities:
            row = (
                self.db.query(EdinetMetricTimeseries)
                .filter_by(sec_code=sec_code, metric_key=metric)
                .order_by(desc(EdinetMetricTimeseries.period_end_year))
                .first()
            )
            if row:
                return {
                    "year": row.period_end_year,
                    "doc_id": row.doc_id,
                    "metric": metric,
                }

        # Fallback to any
        row = (
            self.db.query(EdinetMetricTimeseries)
            .filter_by(sec_code=sec_code)
            .order_by(desc(EdinetMetricTimeseries.period_end_year))
            .first()
        )
        if row:
            return {
                "year": row.period_end_year,
                "doc_id": row.doc_id,
                "metric": "fallback",
            }

        return None

    def _build_facts(self, sec_code: str, year: int, doc_id: str) -> Dict[str, Any]:
        facts = {
            "sec_code": sec_code,
            "period_end_year": year,
            "base_doc_id": doc_id,
            "snapshot": {},
            "delta": {},
            "trend": {},
            "pdf_evidence": [],
            "warnings": [],
        }

        # Snapshot Data
        ts_rows = (
            self.db.query(EdinetMetricTimeseries)
            .filter_by(sec_code=sec_code, period_end_year=year)
            .all()
        )
        for row in ts_rows:
            facts["snapshot"][row.metric_key] = {
                "value": self._fmt_dec(row.value_numeric),
                "display": self._format_display(row.metric_key, row.value_numeric),
            }
            if "end" in row.metric_key:  # ROE_end, ROA_end
                facts["warnings"].append(f"{row.metric_key} is approximation")

        # Delta/Trend Data
        comp_rows = (
            self.db.query(EdinetMetricComparison)
            .filter_by(sec_code=sec_code, period_end_year=year)
            .all()
        )
        for row in comp_rows:
            facts["delta"][row.metric_key] = {
                "yoy_abs": self._fmt_dec(row.yoy_abs),
                "yoy_pct": self._fmt_dec(row.yoy_pct),
                "turnaround": row.turnaround_flag,
            }
            facts["trend"][row.metric_key] = {
                "label": row.trend_label,
                "reason": row.trend_reason,
            }

        # PDF Evidence
        # Check PDF Text Table
        # We need to find text for this doc_id
        # Simple search for keywords
        pdf_texts = (
            self.db.query(EdinetPdfText).filter(EdinetPdfText.doc_id == doc_id).all()
        )

        # Merge all pages? Or search per page?
        # User req: "keyword matches 2+ pages OR snippet >= 80 chars"
        # We'll just scan all pages.

        found_keywords = {}

        for p in pdf_texts:
            content = p.content or ""
            for kw in PDF_KEYWORDS:
                if kw in content:
                    if kw not in found_keywords:
                        found_keywords[kw] = []

                    # Generate simple snippet
                    idx = content.find(kw)
                    start = max(0, idx - 40)
                    end = min(len(content), idx + 100)
                    snippet = content[start:end].replace("\n", " ")

                    found_keywords[kw].append(
                        {"page": p.page_number, "snippet": snippet}
                    )

        # Filter PDF Evidence
        for kw, hits in found_keywords.items():
            valid = False
            # Condition 1: 2 pages
            if len(hits) >= 2:
                valid = True
            # Condition 2: snippet len >= 80 (approx check on first hit)
            # Actually we just check if any hit has long enough context?
            # User said "snippet length >= 80". Snippet generation logic above makes it ~140 chars max.
            # Let's say if we found it, it's likely valid unless OCR failed (too short text).
            # We assume non-OCR for now mostly.
            # But let's strict check the first snippet length.
            if len(hits[0]["snippet"]) >= 80:
                valid = True

            if valid:
                facts["pdf_evidence"].append(
                    {"keyword": kw, "hits": hits[:2]}  # Limit size
                )

        # Sort keys for stability
        return facts

    def _generate_snapshot_text(self, facts: Dict) -> Tuple[str, List[str]]:
        year = facts["period_end_year"]
        snap = facts["snapshot"]

        sales = snap.get("net_sales", {}).get("display", "不明")
        op = snap.get("operating_profit", {}).get("display", "不明")
        op_margin = snap.get("operating_margin", {}).get("display", "不明")
        roe = snap.get("roe_end", {}).get("display", "不明")

        text_body = (
            f"{year}期の実績では、売上高は{sales}、営業利益は{op}となりました。"
            f"営業利益率は{op_margin}で、ROE（期末近似）は{roe}です。"
        )

        bullets = [
            f"売上高: {sales}",
            f"営業利益: {op}",
            f"営業利益率: {op_margin}",
            f"ROE: {roe}",
        ]

        # PDF Mention
        if facts["pdf_evidence"]:
            kws = ",".join([p["keyword"] for p in facts["pdf_evidence"]])
            text_body += f"\n\n参考（開示資料より）: {kws} 等の記述があります。"

        return text_body, bullets

    def _generate_delta_text(self, facts: Dict) -> Tuple[str, List[str]]:
        delta = facts["delta"]

        s_delta = delta.get("net_sales", {})
        i_delta = delta.get("profit_attributable_to_owners", {})  # Net Income

        s_pct = s_delta.get("yoy_pct")
        i_pct = i_delta.get("yoy_pct")

        s_disp = f"{float(s_pct)*100:.1f}%" if s_pct and s_pct != "null" else "算出不可"
        i_disp = f"{float(i_pct)*100:.1f}%" if i_pct and i_pct != "null" else "算出不可"

        # Turnaround check
        s_turn = s_delta.get("turnaround")
        i_turn = i_delta.get("turnaround")

        if s_turn:
            s_disp = s_turn
        if i_turn:
            i_disp = i_turn

        text_body = (
            f"前年同期比では、売上高は{s_disp}、純利益は{i_disp}の変化となりました。"
        )

        bullets = [f"売上変化: {s_disp}", f"利益変化: {i_disp}"]

        return text_body, bullets

    def _format_display(self, key: str, val: Any) -> str:
        if val is None:
            return "-"
        try:
            val_f = float(val)
        except:
            return "-"

        if (
            "rate" in key
            or "margin" in key
            or "roe" in key
            or "roa" in key
            or "ratio" in key
        ):
            # Percentage
            return f"{val_f * 100:.1f}%"
        else:
            # Money (Japan format: 1,234)
            return f"{int(val_f):,}"

    def _fmt_dec(self, val: Any) -> Any:
        # Normalize Decimal to string or null
        if val is None:
            return None
        return str(val)

    def _compute_hash(self, facts: Dict) -> str:
        # Canonical JSON
        s = json.dumps(facts, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(s.encode("utf-8")).hexdigest()

    def _upsert_summary(self, sec_code, year, kind, text_val, bullets, facts, h):
        try:
            stmt = pg_insert(EdinetAISummary).values(
                sec_code=sec_code,
                period_end_year=year,
                kind=kind,
                summary_text=text_val,
                bullet_points=bullets,
                evidence=facts,
                input_hash=h,
            )
            # Do update
            stmt = stmt.on_conflict_do_update(
                index_elements=["sec_code", "period_end_year", "kind"],
                set_={
                    "summary_text": stmt.excluded.summary_text,
                    "bullet_points": stmt.excluded.bullet_points,
                    "evidence": stmt.excluded.evidence,
                    "input_hash": stmt.excluded.input_hash,
                    "updated_at": func.now(),
                },
            )
            self.db.execute(stmt)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Err Summary Upsert: {e}")

    def __del__(self):
        # self.db.close()
        pass
