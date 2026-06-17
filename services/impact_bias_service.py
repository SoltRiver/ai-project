from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime, timedelta
from typing import Dict, List, Any
import logging

from models.stock_impact import (
    StockNews,
    StockNewsAnalysis,
    StockEvent,
    StockEventAnalysis,
)

logger = logging.getLogger(__name__)

IMPACT_LOOKBACK_DAYS = 90
MAX_ITEMS_PER_SIDE = 5


class ImpactBiasService:
    def __init__(self, db: Session):
        self.db = db

    def get_impact_bias(self, sec_code: str) -> Dict[str, Any]:
        """
        Calculate Information Bias (Pos/Neg Ratio) for the last 90 days.
        Returns strict DTO for UI.
        """
        cutoff_date = datetime.now() - timedelta(days=IMPACT_LOOKBACK_DAYS)

        # 1. Fetch News
        news_query = (
            self.db.query(StockNews, StockNewsAnalysis)
            .join(StockNewsAnalysis)
            .filter(StockNews.sec_code == sec_code)
            .filter(StockNews.published_at >= cutoff_date)
        )

        # 2. Fetch Events
        event_query = (
            self.db.query(StockEvent, StockEventAnalysis)
            .join(StockEventAnalysis)
            .filter(StockEvent.sec_code == sec_code)
            .filter(StockEvent.announced_at >= cutoff_date)
        )

        all_items = []

        # Normalize and Collect
        for n, a in news_query.all():
            if a.impact_type in ["POSITIVE", "NEGATIVE"]:
                all_items.append(
                    {
                        "type": "NEWS",
                        "title": n.title,
                        "source": n.source_name,
                        "date": n.published_at,
                        "url": n.url,
                        "impact": a.impact_type,
                        "strength": a.impact_strength,  # HIGH, MEDIUM, LOW
                        "summary": a.summary_2lines,
                    }
                )

        for e, a in event_query.all():
            if a.impact_type in ["POSITIVE", "NEGATIVE"]:
                all_items.append(
                    {
                        "type": "EVENT",
                        "title": e.title,
                        "source": "Disclosure",  # Events are usually disclosures
                        "date": e.announced_at,
                        "url": None,  # Events might not have direct URL in this model yet
                        "impact": a.impact_type,
                        "strength": a.impact_strength,
                        "summary": a.summary_2lines,
                    }
                )

        # 3. Calculate Stats
        pos_items = [x for x in all_items if x["impact"] == "POSITIVE"]
        neg_items = [x for x in all_items if x["impact"] == "NEGATIVE"]

        pos_count = len(pos_items)
        neg_count = len(neg_items)
        total = pos_count + neg_count

        pos_ratio = 0.0
        neg_ratio = 0.0

        if total > 0:
            pos_ratio = pos_count / total
            neg_ratio = neg_count / total

        # 4. Sort (Strength DESC, Date DESC)
        strength_map = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}

        def sort_key(item):
            s_score = strength_map.get(item["strength"], 1)
            return (s_score, item["date"])

        pos_items.sort(key=sort_key, reverse=True)
        neg_items.sort(key=sort_key, reverse=True)

        return {
            "meta": {"lookback_days": IMPACT_LOOKBACK_DAYS, "total_count": total},
            "stats": {
                "pos_count": pos_count,
                "neg_count": neg_count,
                "pos_ratio_pct": round(pos_ratio * 100, 1),
                "neg_ratio_pct": round(neg_ratio * 100, 1),
            },
            "items": {
                "positive": pos_items[:MAX_ITEMS_PER_SIDE],
                "negative": neg_items[:MAX_ITEMS_PER_SIDE],
            },
        }
