"""
イベントクエリサービス

表示用のイベントデータ取得ロジック。
銘柄詳細のイベントカード、カレンダー月グリッド、日別リストのデータを提供。
"""

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from collections import defaultdict

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from models.event import Event

logger = logging.getLogger(__name__)

# 配当サブタイプ全4種
ALL_DIVIDEND_SUBTYPES = ["LAST_CUM", "EX_DATE", "RECORD_DATE", "PAY_DATE"]

# サブタイプの日本語ラベル
SUBTYPE_LABELS = {
    "LAST_CUM": "権利付き最終日",
    "EX_DATE": "権利落ち日",
    "RECORD_DATE": "配当基準日",
    "PAY_DATE": "配当支払開始",
}

# 種別短タグ（UI表示用）
TYPE_SHORT_TAGS = {
    "EARNINGS": "決算",
    "DIVIDEND": "配当",
}

# 状態の日本語ラベル
STATUS_LABELS = {
    "SCHEDULED": "予定",
    "DONE": "実施済",
    "UNKNOWN": "不明",
}


class EventQueryService:
    """
    イベントクエリサービス

    DB からイベントを取得し、UI表示用のデータ構造に変換する。
    """

    def get_stock_event_summary(self, db: Session, code: str) -> Dict[str, Any]:
        """
        銘柄詳細イベントカード用データを取得。

        Returns:
            {
                "next_event": イベント情報 or None,
                "recent_events": [最大3件],
                "dividend_missing": {
                    "has_missing": bool,
                    "missing_labels": [未取得サブタイプの日本語名]
                },
                "has_events": bool
            }
        """
        today = date.today()

        # 未来イベント（次のイベント + 直近リスト用）
        future_events = (
            db.query(Event)
            .filter(Event.stock_code == code, Event.event_date >= today)
            .order_by(Event.event_date.asc())
            .limit(10)
            .all()
        )

        # 過去イベント（直近リスト補完用）
        past_events = (
            db.query(Event)
            .filter(Event.stock_code == code, Event.event_date < today)
            .order_by(Event.event_date.desc())
            .limit(3)
            .all()
        )

        # 次のイベント（未来の最短1件）
        next_event = _format_event(future_events[0]) if future_events else None

        # 直近3件（未来優先 + 過去補完）
        recent = []
        for evt in future_events[:3]:
            recent.append(_format_event(evt))
        # 3件に満たなければ過去から補完
        remaining = 3 - len(recent)
        if remaining > 0:
            for evt in past_events[:remaining]:
                recent.append(_format_event(evt))

        # 配当欠損チェック（最新の配当イベントセットで判定）
        dividend_missing = self._check_dividend_missing(db, code)

        has_events = bool(future_events or past_events)

        return {
            "next_event": next_event,
            "recent_events": recent,
            "dividend_missing": dividend_missing,
            "has_events": has_events,
        }

    def get_month_events(
        self,
        db: Session,
        year: int,
        month: int,
        code: Optional[str] = None,
        types: Optional[List[str]] = None,
        watchlist_codes: Optional[List[str]] = None,
    ) -> Dict[int, Dict[str, Any]]:
        """
        カレンダー月グリッド用データ。

        Returns:
            {日: {"count": N, "tags": ["決算", "配当"], "events": [...]}}
        """
        # 月の範囲を計算
        from calendar import monthrange
        _, last_day = monthrange(year, month)
        start_date = date(year, month, 1)
        end_date = date(year, month, last_day)

        # クエリ構築
        query = db.query(Event).filter(
            Event.event_date >= start_date,
            Event.event_date <= end_date,
        )

        # フィルタ適用
        if code:
            query = query.filter(Event.stock_code == code)
        elif watchlist_codes is not None:
            if watchlist_codes:
                query = query.filter(Event.stock_code.in_(watchlist_codes))
            else:
                # ウォッチリスト空 → 結果なし
                return {}

        if types:
            query = query.filter(Event.event_type.in_(types))

        events = query.order_by(Event.event_date.asc()).all()

        # 日ごとに集計
        day_map: Dict[int, Dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "tags": set(), "events": []}
        )

        for evt in events:
            day = evt.event_date.day
            entry = day_map[day]
            entry["count"] += 1
            entry["tags"].add(TYPE_SHORT_TAGS.get(evt.event_type, evt.event_type))
            entry["events"].append(_format_event(evt))

        # set → list に変換
        result = {}
        for day, info in day_map.items():
            result[day] = {
                "count": info["count"],
                "tags": sorted(info["tags"]),
                "events": info["events"],
            }

        return result

    def get_day_events(
        self,
        db: Session,
        target_date: date,
        code: Optional[str] = None,
        types: Optional[List[str]] = None,
        watchlist_codes: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        当日リスト用データ。

        Returns:
            [イベント情報, ...]（event_date, 種別短タグ, title, 状態）
        """
        query = db.query(Event).filter(Event.event_date == target_date)

        if code:
            query = query.filter(Event.stock_code == code)
        elif watchlist_codes is not None:
            if watchlist_codes:
                query = query.filter(Event.stock_code.in_(watchlist_codes))
            else:
                return []

        if types:
            query = query.filter(Event.event_type.in_(types))

        events = query.order_by(Event.stock_code.asc(), Event.event_type.asc()).all()

        return [_format_event(evt) for evt in events]

    def _check_dividend_missing(self, db: Session, code: str) -> Dict[str, Any]:
        """
        配当4種の欠損状態をチェック。

        直近1年分の配当イベントを確認し、
        取得済みサブタイプと未取得サブタイプを判定する。
        """
        one_year_ago = date.today() - __import__("datetime").timedelta(days=365)
        one_year_ahead = date.today() + __import__("datetime").timedelta(days=365)

        # 直近の配当イベントを取得
        dividend_events = (
            db.query(Event)
            .filter(
                Event.stock_code == code,
                Event.event_type == "DIVIDEND",
                Event.event_date >= one_year_ago,
                Event.event_date <= one_year_ahead,
            )
            .all()
        )

        if not dividend_events:
            # 配当イベント自体がない場合は欠損判定しない
            return {"has_missing": False, "missing_labels": []}

        # 取得済みサブタイプを集計
        found_subtypes = set()
        for evt in dividend_events:
            found_subtypes.add(evt.subtype)

        # 未取得サブタイプ
        missing = []
        for st in ALL_DIVIDEND_SUBTYPES:
            if st not in found_subtypes:
                missing.append(SUBTYPE_LABELS.get(st, st))

        return {
            "has_missing": len(missing) > 0,
            "missing_labels": missing,
        }


# ─── ヘルパー関数 ──────────────────────────

def _format_event(evt: Event) -> Dict[str, Any]:
    """Event モデルをUI表示用の辞書に変換"""
    return {
        "id": evt.id,
        "stock_code": evt.stock_code,
        "event_type": evt.event_type,
        "subtype": evt.subtype,
        "event_date": evt.event_date.isoformat() if evt.event_date else "-",
        "event_date_display": evt.event_date.strftime("%Y-%m-%d") if evt.event_date else "-",
        "title": evt.title,
        "status": evt.status,
        "status_label": STATUS_LABELS.get(evt.status, evt.status),
        "type_tag": TYPE_SHORT_TAGS.get(evt.event_type, evt.event_type),
        "source": evt.source or "-",
        "source_ref": evt.source_ref or "",
        "notes": evt.notes or "",
        "last_verified_at": (
            evt.last_verified_at.strftime("%Y-%m-%d %H:%M")
            if evt.last_verified_at
            else (evt.updated_at.strftime("%Y-%m-%d %H:%M") if evt.updated_at else "-")
        ),
    }


# シングルトン
event_query_service = EventQueryService()
