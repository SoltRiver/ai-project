from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Dict, List, Optional

from candle_classify import get_candle_info
from data_fetcher import (
    fetch_dividends,
    fetch_stock_data,
    fetch_stock_info,
    format_symbol_for_yfinance,
)
from fundamental_fetcher import (
    build_company_scores,
    format_date,
    format_fundamental_value,
    get_event_info,
    get_fundamental_statuses,
    get_key_fundamentals,
)
from stock_name_mapper import STOCK_NAME_MAP


# ウォッチリストのサンプル銘柄
WATCHLIST_CODES = ["7203", "6758", "9984", "8306", "8035"]
# interval に対応する取得期間
PERIOD_BY_INTERVAL = {"1d": "6mo", "1wk": "5y", "1mo": "10y"}
# 表示用ラベル
INTERVAL_LABELS = {"1d": "日足", "1wk": "週足", "1mo": "月足"}

# チャートタブで使う簡易ローソク足パターン
CANDLE_PATTERNS = [
    {
        "name": "包み足 (Bullish Engulfing)",
        "tone": "bullish",
        "summary": "大陽線が前日の実体を包み、流れの転換を示唆。",
        "tip": "出来高増と組み合わせて信頼度を評価。",
    },
    {
        "name": "はらみ線 (Harami)",
        "tone": "neutral",
        "summary": "2本目の実体が1本目に収まる迷いの形。転換の予兆。",
        "tip": "ローソク足単体ではなくサポート/レジスタンスと併せて確認。",
    },
    {
        "name": "たくり線 (Hammer)",
        "tone": "bullish",
        "summary": "下ヒゲの長い小陽線。下落後の反発サインとして注目。",
        "tip": "安値更新後の反発で出来高が伴うか確認する。",
    },
    {
        "name": "首吊り線 (Hanging Man)",
        "tone": "bearish",
        "summary": "上昇局面での下ヒゲ長い小陰陽線。警戒サイン。",
        "tip": "翌日の陰線/出来高増で弱気転換の信頼度が上がる。",
    },
    {
        "name": "三空叩き込み",
        "tone": "bullish",
        "summary": "窓を3連続で開けた下落後の反転シグナル。",
        "tip": "売られ過ぎのサイン。戻り売りラインも合わせて設定。",
    },
]

# 一般用語の用語辞典（用語ページとファンダメンタルタブで利用）
GLOSSARY_TERMS = [
    {
        "term": "PER",
        "meaning": "株価が利益に対して割高か割安かを測る指標。",
        "tip": "業種平均や成長率と合わせて相対評価する。",
    },
    {
        "term": "PBR",
        "meaning": "株価が純資産に対して割高か割安かを測る指標。",
        "tip": "1倍割れは解散価値を下回る目安とされる。",
    },
    {
        "term": "配当利回り",
        "meaning": "投資額に対する配当収入の割合。",
        "tip": "減配リスクや配当性向もセットで確認する。",
    },
    {
        "term": "トレンド",
        "meaning": "価格の方向性（上昇/下降/横ばい）。",
        "tip": "トレンド方向に沿った売買で逆張りリスクを抑える。",
    },
    {
        "term": "サポートライン",
        "meaning": "下げ止まりやすい価格帯。",
        "tip": "割れた場合の損切り基準も事前に決めておく。",
    },
    {
        "term": "レジスタンスライン",
        "meaning": "上げ止まりやすい価格帯。",
        "tip": "ブレイク時は出来高増で信頼度アップ。",
    },
    {
        "term": "ボラティリティ",
        "meaning": "価格変動の大きさを示す度合い。",
        "tip": "高いほど値動きが荒くなるのでポジションサイズに注意。",
    },
]

# ローソク足パターンページ用のカードデータ
CANDLE_PATTERN_CARDS = [
    {
        "name": "大陽線",
        "tone": "bullish",
        "summary": "始値より大きく上昇して終える強い陽線。",
        "hint": "上昇トレンド初動で出ると勢いを示すことが多い。",
    },
    {
        "name": "大陰線",
        "tone": "bearish",
        "summary": "始値より大きく下落して終える強い陰線。",
        "hint": "下落トレンド継続や戻り売りのシグナルになることも。",
    },
    {
        "name": "カラカサ（ハンマー）",
        "tone": "bullish",
        "summary": "下ヒゲが長く実体が短い形。底打ちのサインとして注目。",
        "hint": "安値圏で出来高を伴うと反発期待が高まる。",
    },
    {
        "name": "トンボ（上ヒゲ）",
        "tone": "bearish",
        "summary": "上ヒゲが長く実体が短い形。上値の重さを示しやすい。",
        "hint": "上昇局面で出ると利確売りを意識する場面。",
    },
    {
        "name": "包み足",
        "tone": "bullish",
        "summary": "2本目の実体が1本目を包み込む転換サイン。",
        "hint": "陽線で包み込むと反発、陰線で包み込むと下落の示唆。",
    },
    {
        "name": "はらみ足",
        "tone": "neutral",
        "summary": "2本目の実体が1本目の中に収まる迷いの形。",
        "hint": "レンジ抜けと合わせて方向を見極める。",
    },
    {
        "name": "三空叩き込み",
        "tone": "bullish",
        "summary": "3つ続けて窓を開けて下落後に出る反転シグナル。",
        "hint": "売られ過ぎを示すことが多く、戻り売りラインも設定。",
    },
]

# 株主優待のサンプル
SHAREHOLDER_BENEFITS = {
    "7203": {
        "min_shares": 100,
        "content": "株主優待割引券 / クオカード",
        "months": "3月・9月",
        "note": "長期保有枠で内容が拡充。",
    },
    "6758": {
        "min_shares": 100,
        "content": "ソニー製品の特別販売サイト招待",
        "months": "6月",
        "note": "抽選枠あり。長期保有優遇なし。",
    },
    "9984": {
        "min_shares": 100,
        "content": "通信料割引クーポン（例）",
        "months": "3月",
        "note": "制度上の例示。実際の優待は要確認。",
    },
}


def _display_name(code: str, info_name: Optional[str]) -> str:
    if info_name:
        return info_name
    if code in STOCK_NAME_MAP:
        return STOCK_NAME_MAP[code]
    if code.endswith(".T") and code[:-2] in STOCK_NAME_MAP:
        return STOCK_NAME_MAP[code[:-2]]
    symbol = format_symbol_for_yfinance(code)
    return STOCK_NAME_MAP.get(symbol, code)


def _fmt_currency(value: Optional[float], decimals: int = 2) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float) and math.isnan(value):
        return "N/A"
    fmt = f"¥{{:,.{decimals}f}}"
    return fmt.format(value)


def _fmt_percent(value: Optional[float], decimals: int = 2) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float) and math.isnan(value):
        return "N/A"
    return f"{value * 100:.{decimals}f}%"


def _format_change(change: Optional[float], change_percent: Optional[float]) -> Dict[str, str]:
    if change is None or change_percent is None:
        return {"text": "N/A", "direction": "neutral", "icon": "→"}
    sign = "+" if change > 0 else "-" if change < 0 else "±"
    direction = "up" if change > 0 else "down" if change < 0 else "flat"
    icon = "↑" if change > 0 else "↓" if change < 0 else "→"
    text = f"{sign}{_fmt_currency(abs(change))} ({sign}{abs(change_percent):.2f}%)"
    return {"text": text, "direction": direction, "icon": icon}


def _calc_high_low(symbol: str) -> tuple[Optional[float], Optional[float]]:
    history = fetch_stock_data(symbol, period="6mo", interval="1d")
    if history is None or getattr(history, "empty", True):
        return None, None
    return (
        float(history["high"].max(skipna=True)),
        float(history["low"].min(skipna=True)),
    )


def get_stock_list() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for code in WATCHLIST_CODES:
        symbol = format_symbol_for_yfinance(code)
        info = fetch_stock_info(symbol)
        high, low = _calc_high_low(symbol)
        if high is not None:
            high = math.floor(high)
        if low is not None:
            low = math.floor(low)
        change = _format_change(
            info.get("change") if info else None,
            info.get("change_percent") if info else None,
        )
        rows.append(
            {
                "code": code,
                "name": _display_name(code, info.get("name") if info else None),
                "current_price": _fmt_currency(info.get("current_price") if info else None),
                "change_text": change["text"],
                "change_direction": change["direction"],
                "change_icon": change["icon"],
                "high_low": f"{_fmt_currency(high)} / {_fmt_currency(low)}",
            }
        )
    return rows


def get_stock_header(code: str) -> Optional[Dict[str, Any]]:
    symbol = format_symbol_for_yfinance(code)
    info = fetch_stock_info(symbol)
    if info is None:
        return None
    change = _format_change(info.get("change"), info.get("change_percent"))
    return {
        "code": code,
        "symbol": symbol,
        "name": _display_name(code, info.get("name")),
        "current_price": _fmt_currency(info.get("current_price")),
        "change_text": change["text"],
        "change_direction": change["direction"],
        "change_icon": change["icon"],
        "exchange": info.get("exchange") or "",
        "industry": info.get("industry") or "",
        "currency": info.get("currency") or "JPY",
    }


def _trend_label(first: Optional[float], last: Optional[float]) -> str:
    if first is None or last is None:
        return "データ未取得"
    if last > first:
        return "上昇基調"
    if last < first:
        return "下降基調"
    return "横ばい"


def _build_chart_points(history, limit: int = 20) -> List[Dict[str, str]]:
    points: List[Dict[str, str]] = []
    if history is None or getattr(history, "empty", True):
        return points
    trimmed = history.tail(limit)
    for _, row in trimmed.iterrows():
        date_value = row["date"]
        if isinstance(date_value, datetime):
            date_label = date_value.strftime("%Y-%m-%d")
        else:
            date_label = str(date_value)[:10]
        points.append(
            {
                "date": date_label,
                "open": float(row["open"]),
                "close": _fmt_currency(float(row["close"])),
                "high": _fmt_currency(float(row["high"])),
                "low": _fmt_currency(float(row["low"])),
                "open_raw": float(row["open"]),
                "close_raw": float(row["close"]),
                "high_raw": float(row["high"]),
                "low_raw": float(row["low"]),
            }
        )
    return points


def get_chart_tab(code: str, interval: str = "1d") -> Dict[str, Any]:
    normalized_interval = interval if interval in PERIOD_BY_INTERVAL else "1d"
    symbol = format_symbol_for_yfinance(code)
    history = fetch_stock_data(
        symbol,
        period=PERIOD_BY_INTERVAL[normalized_interval],
        interval=normalized_interval,
    )

    if history is None or getattr(history, "empty", True):
        return {
            "interval": normalized_interval,
            "interval_label": INTERVAL_LABELS[normalized_interval],
            "interval_options": [{"label": INTERVAL_LABELS[k], "value": k} for k in ("1d", "1wk", "1mo")],
            "chart_summary": {},
            "chart_points": [],
            "candle_popup": [],
            "candle_type": "N/A",
            "patterns": CANDLE_PATTERNS,
            "trend_label": "データ未取得",
            "support_resistance": {},
            "signals": [],
            "risks": [],
        }

    latest = history.iloc[-1]
    previous = history.iloc[-2] if len(history) > 1 else None
    change_val = None
    change_pct = None
    if previous is not None:
        change_val = float(latest["close"]) - float(previous["close"])
        if previous["close"]:
            change_pct = (change_val / float(previous["close"])) * 100

    change = _format_change(change_val, change_pct)
    high_val = float(history["high"].max(skipna=True))
    low_val = float(history["low"].min(skipna=True))

    candle_info = get_candle_info(
        float(latest["open"]),
        float(latest["high"]),
        float(latest["low"]),
        float(latest["close"]),
    )

    candle_popup = [
        {"label": "始値", "value": _fmt_currency(candle_info.get("open"))},
        {"label": "高値", "value": _fmt_currency(candle_info.get("high"))},
        {"label": "安値", "value": _fmt_currency(candle_info.get("low"))},
        {"label": "終値", "value": _fmt_currency(candle_info.get("close"))},
        {"label": "値幅", "value": _fmt_currency(candle_info.get("total_range"))},
    ]

    first_close = float(history["close"].iloc[0]) if len(history) else None
    chart_points = _build_chart_points(history)

    chart_summary = {
        "last_close": _fmt_currency(float(latest["close"])),
        "open": _fmt_currency(float(latest["open"])),
        "high": _fmt_currency(high_val),
        "low": _fmt_currency(low_val),
        "change_text": change["text"],
        "change_direction": change["direction"],
        "change_icon": change["icon"],
        "range": f"{_fmt_currency(high_val)} / {_fmt_currency(low_val)}",
    }

    support_resistance = {
        "support": _fmt_currency(low_val),
        "resistance": _fmt_currency(high_val),
        "description": "直近の安値・高値を目安にサポート/レジスタンスを表示しています。",
    }

    signals = [
        {
            "label": "ゴールデンクロス",
            "status": "参考",
            "note": "短期線が長期線を上抜けると上昇トレンド転換の参考になります。",
        },
        {
            "label": "RSI",
            "status": "中立",
            "note": "RSIが50付近で推移。売られすぎ/買われすぎの極端な状態ではありません。",
        },
    ]

    risks = [
        "価格変動が大きめの銘柄です。",
        "売買が成立しにくい場合があります。",
    ]

    return {
        "interval": normalized_interval,
        "interval_label": INTERVAL_LABELS[normalized_interval],
        "interval_options": [{"label": INTERVAL_LABELS[k], "value": k} for k in ("1d", "1wk", "1mo")],
        "chart_summary": chart_summary,
        "chart_points": chart_points,
        "candle_popup": candle_popup,
        "candle_type": candle_info.get("type"),
        "patterns": CANDLE_PATTERNS,
        "trend_label": _trend_label(first_close, float(latest["close"])),
        "support_resistance": support_resistance,
        "signals": signals,
        "risks": risks,
    }


def _format_fundamentals(fundamental_data: Dict[str, Any]) -> List[Dict[str, str]]:
    format_map = {
        "PER": "float",
        "PBR": "float",
        "配当利回り": "percent",
        "自己資本比率": "float",
        "ROE": "percent",
        "ROA": "percent",
        "利益率": "percent",
        "beta": "float",
    }
    items: List[Dict[str, str]] = []
    for key, value in fundamental_data.items():
        if key in ("earnings_date", "ex_dividend_date"):
            continue
        fmt_type = format_map.get(key, "float")
        items.append(
            {
                "label": key,
                "value": format_fundamental_value(value, fmt_type),
            }
        )
    return items


def get_fundamental_tab(code: str) -> Dict[str, Any]:
    symbol = format_symbol_for_yfinance(code)
    fundamentals_raw = get_key_fundamentals(symbol)
    if fundamentals_raw is None:
        return {
            "fundamentals": [],
            "statuses": {},
            "scores": {},
            "events": {},
            "glossary": GLOSSARY_TERMS,
            "timings": {},
            "risks": [],
        }
    statuses = get_fundamental_statuses(fundamentals_raw)
    scores = build_company_scores(fundamentals_raw)
    events = get_event_info(symbol, fundamental_data=fundamentals_raw) or {}

    fundamental_items = _format_fundamentals(fundamentals_raw)
    events_display = {
        "決算発表": format_date(events.get("earnings_date")),
        "配当権利落ち": format_date(events.get("ex_dividend_date")),
        "配当利回り": format_fundamental_value(events.get("dividend_yield"), "percent"),
        "配当額": format_fundamental_value(events.get("dividend_rate"), "float"),
    }

    timings = {
        "短期": "押し目買いは直近サポート付近を目安に、損切りラインを明確に設定。",
        "中期": "業績トレンドとセクター動向を見つつ、レジスタンス突破で買い増し検討。",
        "長期": "長期保有前提なら配当利回りと成長性をチェックし、割安圏でコツコツ分散。",
        "注意": "あくまで参考情報であり、実際の値動きを保証するものではありません。",
    }

    risks = [
        "価格変動が大きめの銘柄です。",
        "売買が成立しにくい場合があります。",
    ]

    return {
        "fundamentals": fundamental_items,
        "statuses": statuses,
        "scores": scores,
        "events": events_display,
        "glossary": GLOSSARY_TERMS,
        "timings": timings,
        "risks": risks,
    }


def get_dividend_tab(code: str) -> Dict[str, Any]:
    symbol = format_symbol_for_yfinance(code)
    dividends = fetch_dividends(symbol, limit=8)
    records: List[Dict[str, str]] = []
    for record in dividends:
        date_val = record.get("date")
        if isinstance(date_val, datetime):
            date_display = date_val.strftime("%Y-%m-%d")
        else:
            date_display = str(date_val)
        records.append(
            {
                "date": date_display,
                "amount": _fmt_currency(record.get("amount"), decimals=2),
            }
        )

    fundamentals_raw = get_key_fundamentals(symbol)
    current_yield = None
    if fundamentals_raw is not None:
        current_yield = fundamentals_raw.get("配当利回り")

    yield_info = {
        "yield": format_fundamental_value(current_yield, "percent") if current_yield is not None else "N/A",
        "policy": "安定配当を目指します（参考情報）。",
    }

    return {"dividends": records, "yield_info": yield_info}


def get_shareholder_tab(code: str) -> Dict[str, Any]:
    benefit = SHAREHOLDER_BENEFITS.get(code) or SHAREHOLDER_BENEFITS.get(code.replace(".T", ""))
    return {"benefit": benefit}


def get_glossary_terms() -> List[Dict[str, str]]:
    return GLOSSARY_TERMS


def get_candle_patterns_page() -> List[Dict[str, str]]:
    return CANDLE_PATTERN_CARDS


def get_timestamp_label() -> str:
    now = datetime.now()
    return now.strftime("（%Y/%m/%d %H:%M 時点）")
