from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from analyzer import (
    add_technical_indicators,
    analyze_candlestick,
    calculate_trendline,
    detect_dead_cross,
    detect_golden_cross,
    get_direction_label,
)
from candle_classify import get_candle_info
from data_fetcher import (
    fetch_dividends,
    fetch_realtime_data,
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
from terms_data import TERMS_DATA
from services.financial_analyzer import FinancialAnalyzer

# Initialize analyzer
analyzer = FinancialAnalyzer()

# ウォッチリストのサンプル銘柄
WATCHLIST_CODES = ["7203", "6758", "9984", "8306", "8035"]

# interval に対応する取得期間
PERIOD_BY_INTERVAL = {
    "1m": "7d",
    "5m": "60d",
    "10m": "60d",
    "1d": "5y",
    "1wk": "5y",
    "1mo": "10y",
}

INTERVAL_LABELS = {
    "1m": "1分足",
    "5m": "5分足",
    "10m": "10分足",
    "1d": "日足",
    "1wk": "週足",
    "1mo": "月足",
}

INTRADAY_INTERVALS = {"1m", "5m", "10m"}


def _build_glossary_terms() -> List[Dict[str, str]]:
    terms: List[Dict[str, str]] = []
    for category, items in TERMS_DATA.items():
        for key, term in items.items():
            terms.append(
                {
                    "term": term.get("japanese") or key,
                    "meaning": term.get("meaning") or "",
                    "tip": term.get("usage") or "",
                    "category": category,
                }
            )
    return terms


GLOSSARY_TERMS = _build_glossary_terms()

# ローソク足パターンのカードデータ
CANDLE_PATTERN_CARDS = [
    {
        "id": "big_bull",
        "name": "大陽線",
        "group": "basic",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/big_bull.svg",
        "catch": "強い買い圧力が続くサイン",
        "desc_lead": "流れを変える長い陽線",
        "desc_body": "始値から大きく上昇し、実体が長くなる形です。",
        "detail_desc": "材料が出た直後やトレンド転換の初動で現れやすい長い陽線です。出来高が伴えば信頼度が上がります。",
        "scene": "好材料発表直後や強い反発場面",
        "howto": "実体の長さと出来高の増加を確認する",
        "notes": ["出来高が増えているか確認", "翌日の反落に注意"],
    },
    {
        "id": "hammer",
        "name": "下ヒゲ陽線（ハンマー）",
        "group": "basic",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/hammer.svg",
        "catch": "下げ止まりの兆し",
        "desc_lead": "押し目で出やすい形",
        "desc_body": "長い下ヒゲと小さい実体が特徴。買い戻しが強いときに出ます。",
        "detail_desc": "一時大きく売られたものの、引けにかけて買い戻されたサインです。サポート付近で出ると反発候補になります。",
        "scene": "下落トレンドの終盤やサポート付近",
        "howto": "下ヒゲの長さと直近安値との位置関係を見る",
        "notes": ["出来高増加なら信頼度アップ"],
    },
    {
        "id": "doji",
        "name": "十字線",
        "group": "basic",
        "category": "迷い",
        "tone": "neutral",
        "svg": "images/doji.svg",
        "catch": "方向感が定まらない",
        "desc_lead": "売り買い拮抗",
        "desc_body": "始値と終値がほぼ同じで、迷いの局面で出やすい形です。",
        "detail_desc": "上昇・下落どちらかの勢いが弱まったサイン。直後の足の方向で次の流れを判断します。",
        "scene": "トレンド転換の手前や重要イベント前",
        "howto": "前後のローソク足の形と並べて確認する",
        "notes": ["出来高が減少しているかも確認"],
    },
    {
        "id": "big_bear",
        "name": "大陰線",
        "group": "basic",
        "category": "陰線",
        "tone": "bearish",
        "svg": "images/big_bear.svg",
        "catch": "売りが強く下落が続くサイン",
        "desc_lead": "流れを変える長い陰線",
        "desc_body": "始値から大きく下落し、実体が長くなる形です。",
        "detail_desc": "悪材料直後やトレンド転換の初動で現れやすい陰線です。出来高が伴えば信頼度が上がります。",
        "scene": "悪材料発表直後や急落局面",
        "howto": "実体の長さと出来高の増加を確認する",
        "notes": ["出来高が増えているか確認", "翌日の自律反発に注意"],
    },
    {
        "id": "shooting_star",
        "name": "上ヒゲ陰線（流れ弱まり）",
        "group": "basic",
        "category": "陰線",
        "tone": "bearish",
        "svg": "images/shooting_star.svg",
        "catch": "上値で売りが強いサイン",
        "desc_lead": "天井圏での失速",
        "desc_body": "長い上ヒゲと小さな実体が特徴。高値で売りが優勢になった形です。",
        "detail_desc": "上昇トレンドの高値圏で出ると反落サインとして見られます。出来高が増加していると注意。",
        "scene": "上昇トレンドの高値圏",
        "howto": "上ヒゲの長さと直近高値との位置関係を見る",
        "notes": ["翌日の陰線確認で信頼度アップ"],
    },
    {
        "id": "bull_engulfing",
        "name": "包み足（陽）",
        "group": "advanced",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/bull_engulfing.svg",
        "catch": "前日の陰線を包む強い買い",
        "desc_lead": "反転の候補",
        "desc_body": "小さな陰線を大きな陽線が実体で包み込む形。",
        "detail_desc": "連続陰線のあとに出ると転換サインとして扱われます。出来高が伴うと信頼度が上がります。",
        "scene": "下落トレンド終盤の押し目",
        "howto": "実体の大きさと出来高を確認",
        "notes": ["直近安値の更新有無を確認"],
    },
    {
        "id": "three_white_soldiers",
        "name": "赤三兵",
        "group": "advanced",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/three_white_soldiers.svg",
        "catch": "3本続く強気",
        "desc_lead": "力強い上昇",
        "desc_body": "陽線が3本連続し、始値が前日の実体内から始まる形。",
        "detail_desc": "安値圏で出ると転換サイン。高値圏では過熱感にも注意。",
        "scene": "下落後の反発局面",
        "howto": "3本の実体が揃って長いか確認",
        "notes": ["過熱感と出来高の伸びに注意"],
    },
    {
        "id": "rising_three_methods",
        "name": "切り上げ三法",
        "group": "advanced",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/rising_three_methods.svg",
        "catch": "上昇中の一服",
        "desc_lead": "押し目で再上昇",
        "desc_body": "大陽線のあと小さな陰線が続き、再度陽線で上抜ける形。",
        "detail_desc": "上昇トレンドの途中に出る継続パターン。押し目買いの好機。",
        "scene": "上昇トレンド中の調整局面",
        "howto": "陰線群が大陽線の実体内に収まっているか確認",
        "notes": ["上抜けの出来高が増えていると◎"],
    },
    {
        "id": "bear_engulfing",
        "name": "包み足（陰）",
        "group": "advanced",
        "category": "陰線",
        "tone": "bearish",
        "svg": "images/bear_engulfing.svg",
        "catch": "前日の陽線を包む強い売り",
        "desc_lead": "天井圏で警戒",
        "desc_body": "陽線を大きな陰線が実体で包み込む形。",
        "detail_desc": "高値圏で出ると反落サイン。出来高を伴うと下落継続に注意。",
        "scene": "高値圏での反落局面",
        "howto": "実体の長さと前日の高値更新有無を確認",
        "notes": ["直近サポートとの距離を確認"],
    },
    {
        "id": "three_black_crows",
        "name": "黒三兵",
        "group": "advanced",
        "category": "陰線",
        "tone": "bearish",
        "svg": "images/three_black_crows.svg",
        "catch": "3本続く弱気",
        "desc_lead": "下落圧力が強い",
        "desc_body": "陰線が3本連続し、始値が前日の実体内から始まる形。",
        "detail_desc": "天井圏での出現はトレンド転換の警戒シグナル。安値圏では行き過ぎにも注意。",
        "scene": "上昇後の失速局面",
        "howto": "3本とも実体が長いかを確認",
        "notes": ["出来高増なら強い下落圧力"],
    },
    {
        "id": "falling_three_methods",
        "name": "切り下げ三法",
        "group": "advanced",
        "category": "陰線",
        "tone": "bearish",
        "svg": "images/falling_three_methods.svg",
        "catch": "下落中の戻り売り",
        "desc_lead": "戻りで再下落",
        "desc_body": "大陰線のあと小さな陽線が続き、再度陰線で下抜ける形。",
        "detail_desc": "下落トレンド継続のサイン。戻り売りが優勢なときに出ます。",
        "scene": "下落トレンド中の戻り局面",
        "howto": "陽線群が大陰線の実体内に収まるか確認",
        "notes": ["出来高が減れば弱気継続に警戒"],
    },
    {
        "id": "harami",
        "name": "はらみ足",
        "group": "advanced",
        "category": "迷い",
        "tone": "neutral",
        "svg": "images/harami.svg",
        "catch": "値動きが一旦収縮",
        "desc_lead": "方向感が出にくい",
        "desc_body": "2本目の足が1本目の実体内に収まる形。",
        "detail_desc": "動きが小休止しているサイン。次の足で方向を確認。",
        "scene": "トレンド転換前後",
        "howto": "ブレイク方向と出来高を確認",
        "notes": ["直近のサポレジを併せて見る"],
    },
    {
        "id": "inside_range",
        "name": "インサイドレンジ",
        "group": "advanced",
        "category": "迷い",
        "tone": "neutral",
        "svg": "images/inside_range.svg",
        "catch": "レンジが続く",
        "desc_lead": "様子見ムード",
        "desc_body": "複数本の足が同じ価格帯に収まるレンジ状態。",
        "detail_desc": "ブレイク方向で次の流れが決まるため、サポート・レジスタンス付近を注視。",
        "scene": "イベント前の持ち合い",
        "howto": "レンジ上限下限を引いておく",
        "notes": ["出来高が減っていれば持ち合い継続の可能性"],
    },
    {
        "id": "multiple_doji",
        "name": "連続十字線",
        "group": "advanced",
        "category": "迷い",
        "tone": "neutral",
        "svg": "images/multiple_doji.svg",
        "catch": "迷いが続く",
        "desc_lead": "方向感なし",
        "desc_body": "十字線が連続し、売り買いが拮抗している形。",
        "detail_desc": "イベント待ちや材料待ちで出やすい。ブレイク方向に一気に動くことも。",
        "scene": "重要指標や決算前",
        "howto": "ブレイク時の出来高と方向を重視",
        "notes": ["上下のヒゲが伸びる場合はボラティリティ注意"],
    },
]


def _jp_name(code: str, fetched_name: Optional[str]) -> str:
    base = STOCK_NAME_MAP.get(code) or fetched_name or code
    return f"{base}（{code}）"


def _fmt_price(value: Optional[float], decimals: int = 1, floor: bool = False) -> str:
    if value is None:
        return "N/A"
    if floor:
        return f"¥{math.floor(value):,}"
    return f"¥{value:,.{decimals}f}"


def _format_change(current: Optional[float], previous: Optional[float]) -> Dict[str, Any]:
    if current is None or previous is None:
        return {"text": "N/A", "direction": "flat", "icon": "→"}
    diff = current - previous
    pct = (diff / previous) * 100 if previous else 0
    sign = "+" if diff > 0 else "-" if diff < 0 else "±"
    direction = "up" if diff > 0 else "down" if diff < 0 else "flat"
    icon = "↑" if diff > 0 else "↓" if diff < 0 else "→"
    text = f"{sign}¥{abs(diff):,.0f}（{sign}{abs(pct):.2f}%）"
    return {"text": text, "direction": direction, "icon": icon, "diff": diff, "pct": pct}


def _build_points(df: pd.DataFrame, interval: str) -> List[Dict[str, Any]]:
    if df is None or df.empty:
        return []
    points: List[Dict[str, Any]] = []
    date_col = "date" if "date" in df.columns else df.columns[0]
    label_fmt = "%H:%M" if interval in INTRADAY_INTERVALS else "%Y/%m/%d"
    
    # Identify SMA columns
    sma_cols = [c for c in df.columns if c.startswith("SMA")]

    for _, row in df.iterrows():
        date_val = row[date_col]
        label = date_val.strftime(label_fmt)
        
        # Analyze Candlestick
        candlestick = analyze_candlestick(
            open_price=row['open'],
            high=row['high'],
            low=row['low'],
            close=row['close']
        )

        point = {
            "label": label,
            "open": round(float(row["open"]), 1),
            "high": round(float(row["high"]), 1),
            "low": round(float(row["low"]), 1),
            "close": round(float(row["close"]), 1),
            "volume": int(row["volume"]) if not pd.isna(row.get("volume", None)) else 0,
            "candle_name": candlestick['name'],
            "candle_type": candlestick['type'],
        }
        # Add SMA values
        for col in sma_cols:
            val = row[col]
            point[col] = round(float(val), 1) if not pd.isna(val) else None

        try:
            candle = get_candle_info(point["open"], point["high"], point["low"], point["close"])
            point["pattern"] = candle.get("type")
        except Exception:
            point["pattern"] = None
        points.append(point)
    return points


def _support_levels(points: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not points:
        return []
    closes = [p["close"] for p in points]
    min_close = min(closes)
    max_close = max(closes)
    mid = (min_close + max_close) / 2
    return [
        {"value": round(min_close, 1), "type": "support", "label": "サポート", "note": "過去に下げ止まった価格帯"},
        {"value": round(mid, 1), "type": "neutral", "label": "注目価格", "note": "出来高が集まりやすい水準"},
        {"value": round(max_close, 1), "type": "resistance", "label": "レジスタンス", "note": "過去に売られやすかった価格帯"},
    ]


def _trend_label(points: List[Dict[str, Any]]) -> str:
    if not points:
        return "トレンド不明"
    closes = pd.Series([p["close"] for p in points])
    return get_direction_label(closes, positive_label="上昇傾向", negative_label="下落傾向", neutral_label="もみ合い（レンジ相場）")


def _build_signals(points: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    if len(points) < 5:
        return [
            {"title": "ゴールデンクロス", "detail": "データが不足しています", "tone": "neutral"},
            {"title": "RSI", "detail": "データが不足しています", "tone": "neutral"},
            {"title": "MACD", "detail": "データが不足しています", "tone": "neutral"},
            {"title": "支持線・抵抗線", "detail": "サポート・レジスタンスを確認してください", "tone": "neutral"},
        ]

    closes = pd.Series([p["close"] for p in points])
    tech_df = add_technical_indicators(pd.DataFrame({"close": closes}))
    golden = detect_golden_cross(tech_df["SMA25"], tech_df["SMA75"])
    dead = detect_dead_cross(tech_df["SMA25"], tech_df["SMA75"])
    rsi_val = tech_df["RSI"].iloc[-1] if "RSI" in tech_df else None
    rsi_label = "買われすぎ" if rsi_val is not None and rsi_val >= 70 else "売られすぎ" if rsi_val is not None and rsi_val <= 30 else "中立"
    signals = [
        {
            "title": "ゴールデンクロス／デッドクロス",
            "detail": "短期線が長期線を上抜けると上昇、下抜けると下落のサインです。",
            "tone": "positive" if golden else "negative" if dead else "neutral",
        },
        {
            "title": "RSIの買われすぎ／売られすぎ",
            "detail": f"RSI {rsi_val:.1f} で {rsi_label} 判定です。" if rsi_val is not None else "RSIは計算中です。",
            "tone": "negative" if rsi_val is not None and rsi_val >= 70 else "positive" if rsi_val is not None and rsi_val <= 30 else "neutral",
        },
        {
            "title": "MACDの方向性",
            "detail": "MACDラインとシグナルの方向で勢いを確認しましょう。",
            "tone": "neutral",
        },
        {
            "title": "支持線／抵抗線の位置",
            "detail": "サポート・レジスタンス近辺では反発や反落に注意してください。",
            "tone": "neutral",
        },
    ]
    return signals


def _build_risks(points: List[Dict[str, Any]], info: Optional[Dict[str, Any]]) -> List[str]:
    if not points:
        return ["データ不足のためリスク評価ができません。"]
    closes = pd.Series([p["close"] for p in points])
    returns = closes.pct_change().dropna()
    if returns.empty:
        vol_level = "データ不足"
        vol_warn = False
    else:
        vol = float(returns.std() * 100)
        if vol >= 3.0:
            vol_level = "ボラティリティが高い"
            vol_warn = True
        elif vol >= 1.5:
            vol_level = "ボラティリティは普通"
            vol_warn = False
        else:
            vol_level = "ボラティリティは落ち着き"
            vol_warn = False

    volume_basis = None
    if info:
        volume_basis = info.get("average_volume") or info.get("volume")
    if volume_basis is None:
        liquidity_level = "出来高データ不足"
        liquidity_warn = False
    elif volume_basis < 50000:
        liquidity_level = "流動性が低い"
        liquidity_warn = True
    else:
        liquidity_level = "流動性は良好"
        liquidity_warn = False

    risks = [
        f"{vol_level}（値動きの大きさを確認）",
        f"{liquidity_level}（急減・急増に注意）",
        "悪材料ニュースがないか最新の見出しを確認",
        "決算発表前後は値動きが荒くなる可能性",
        "権利付き最終日付近は配当・優待目的の売買が増えます",
    ]
    return risks


def _build_positives(points: List[Dict[str, Any]]) -> List[str]:
    if not points:
        return ["データ不足のためプラス要素を表示できません。"]
    return [
        "好材料ニュースが出ていないか確認し、追い風ならエントリー検討",
        "業績が改善傾向なら中長期での上昇余地あり",
        "増配や優待改善は長期保有の追い風",
        "同業他社も強ければセクター全体が支えになる",
        "為替や金利など外部環境が追い風の場合は上昇が続きやすい",
    ]


def get_stock_list() -> List[Dict[str, Any]]:
    stocks: List[Dict[str, Any]] = []
    for code in WATCHLIST_CODES:
        symbol = format_symbol_for_yfinance(code)
        info = fetch_stock_info(symbol) or {}
        display_name = _jp_name(code, info.get("name"))
        history = fetch_stock_data(symbol, period="1mo", interval="1d")
        high_low_text = "N/A"
        if history is not None and not history.empty:
            high_val = float(history["high"].max())
            low_val = float(history["low"].min())
            high_low_text = f"高値 {math.floor(high_val):,} / 安値 {math.floor(low_val):,}"

        change = _format_change(info.get("current_price"), info.get("previous_close"))
        stocks.append(
            {
                "code": code,
                "name": display_name,
                "current_price": _fmt_price(info.get("current_price"), decimals=1),
                "change_direction": change["direction"],
                "change_icon": change["icon"],
                "change_text": change["text"],
                "high_low": high_low_text,
            }
        )
    return stocks


def get_stock_header(code: str) -> Optional[Dict[str, Any]]:
    symbol = format_symbol_for_yfinance(code)
    info = fetch_stock_info(symbol)
    if info is None:
        return None
    display_name = _jp_name(code, info.get("name"))
    change = _format_change(info.get("current_price"), info.get("previous_close"))
    return {
        "code": code,
        "display_name": display_name,
        "price_text": _fmt_price(info.get("current_price"), decimals=1),
        "change_text": change["text"],
        "change_direction": change["direction"],
        "change_icon": change["icon"],
        "previous_close": info.get("previous_close"),
        "open": info.get("open") or "",
        "high": info.get("dayHigh") or "",
        "low": info.get("dayLow") or "",
    }


def get_chart_tab(code: str, interval: str = "1d") -> Dict[str, Any]:
    symbol = format_symbol_for_yfinance(code)
    df = fetch_stock_data(symbol, period=PERIOD_BY_INTERVAL.get(interval, "1mo"), interval=interval)
    
    # Calculate SMAs
    sma_periods = [25, 75, 200]  # Default for daily
    if interval == "1wk":
        sma_periods = [13, 26, 52]
    elif interval == "1mo":
        sma_periods = [12, 24, 60]
    elif interval in INTRADAY_INTERVALS:
        sma_periods = [] # No SMA for intraday for now, or maybe small ones
    
    if df is not None and not df.empty and sma_periods:
        df = add_technical_indicators(df, sma_periods=sma_periods)

    points = _build_points(df if df is not None else pd.DataFrame(), interval)
    support_levels = _support_levels(points)
    trend_label = _trend_label(points)
    signals = _build_signals(points)

    if df is not None and not df.empty:
        last_row = df.iloc[-1]
        prev_close = df.iloc[-2]["close"] if len(df) >= 2 else last_row["close"]
        change = _format_change(last_row["close"], prev_close)
        chart_summary = {
            "last_close": _fmt_price(last_row["close"], decimals=1),
            "open": _fmt_price(last_row["open"], decimals=1),
            "high": _fmt_price(last_row["high"], decimals=1),
            "low": _fmt_price(last_row["low"], decimals=1),
            "change_text": change["text"],
            "change_direction": change["direction"],
            "change_icon": change["icon"],
            "timestamp": last_row["date"].strftime("%Y/%m/%d %H:%M") if hasattr(last_row["date"], "strftime") else "",
        }
    else:
        chart_summary = {
            "last_close": "N/A",
            "open": "N/A",
            "high": "N/A",
            "low": "N/A",
            "change_text": "N/A",
            "change_direction": "flat",
            "change_icon": "→",
            "timestamp": "",
        }

    axis_note = "縦軸：価格（小数第1位） / 横軸：時間（HH:mm）" if interval in INTRADAY_INTERVALS else "縦軸：価格（小数第1位） / 横軸：時間（yyyy/mm/dd）"

    info = fetch_realtime_data(symbol) or {}
    risks = _build_risks(points, info)
    positives = _build_positives(points)

    interval_options = [{"value": key, "label": label} for key, label in INTERVAL_LABELS.items()]

    return {
        "interval": interval,
        "interval_options": interval_options,
        "chart_summary": chart_summary,
        "trend_label": trend_label,
        "chart_payload": {"points": points, "support_levels": support_levels},
        "support_levels": support_levels,
        "signals": signals,
        "risks": risks,
        "positives": positives,
        "axis_note": axis_note,
    }


def get_fundamental_tab(code: str) -> Dict[str, Any]:
    # 1. Fetch original data (Yahoo Finance based) for existing UI components
    symbol = format_symbol_for_yfinance(code)
    fundamental = get_key_fundamentals(symbol) or {}
    fundamental_groups = [
        {
            "subtitle": "割安性評価",
            "items": [
                {"label": "PER", "value": format_fundamental_value(fundamental.get("PER"), "float")},
                {"label": "PBR", "value": format_fundamental_value(fundamental.get("PBR"), "float")},
            ]
        },
        {
            "subtitle": "財務・収益性",
            "items": [
                {"label": "ROE", "value": format_fundamental_value(fundamental.get("ROE"), "percent")},
                {"label": "自己資本比率", "value": format_fundamental_value(fundamental.get("自己資本比率"), "percent")},
            ]
        },
        {
            "subtitle": "配当",
            "items": [
                {"label": "配当利回り", "value": format_fundamental_value(fundamental.get("配当利回り"), "percent")},
            ]
        }
    ]
    statuses = get_fundamental_statuses(fundamental)
    scores = build_company_scores(fundamental)
    events = get_event_info(symbol, fundamental) or {}
    timings = {
        "決算発表日": format_date(events.get("earnings_date")),
        "配当基準日": format_date(events.get("ex_dividend_date")),
        "権利付き最終日": "要確認",
    }
    # 1.5 Fetch chart data for dynamic Risk/Positive calculation
    # Use 6mo daily data for standard volatility analysis
    chart_df = fetch_stock_data(symbol, period="6mo", interval="1d")
    points = _build_points(chart_df, "1d")
    
    # Calculate risks and positives dynamically
    # Note: info is already fetched as 'fundamental' dict, but _build_risks expects yfinance info dict structure for volume
    # We can fetch fresh realtime info or approximate. Let's fetch realtime for accuracy on volume.
    realtime_info = fetch_realtime_data(symbol) or {}
    risks = _build_risks(points, realtime_info)
    
    # 2. Fetch new EDINET Analysis data
    try:
        analysis = analyzer.analyze_stock(code)
    except Exception as e:
        print(f"Error fetching fundamental data for {code}: {e}")
        analysis = {"error": str(e)}

    glossary = GLOSSARY_TERMS[:6]
    
    return {
        "fundamental_groups": fundamental_groups,
        "statuses": statuses,
        "scores": scores,
        "events": {
            "決算発表": format_date(events.get("earnings_date")),
            "配当権利落ち": format_date(events.get("ex_dividend_date")),
        },
        "timings": timings,
        "risks": risks,
        "positives": _build_positives(points),  # Added positives
        "glossary": glossary,
        "analysis": analysis  # Added new data
    }


def get_dividend_tab(code: str) -> Dict[str, Any]:
    symbol = format_symbol_for_yfinance(code)
    dividends = fetch_dividends(symbol, limit=5)
    rows = []
    for item in dividends:
        date_val = item.get("date")
        if hasattr(date_val, "strftime"):
            date_str = date_val.strftime("%Y/%m/%d")
        else:
            date_str = str(date_val)
        rows.append({"date": date_str, "amount": _fmt_price(item.get("amount"), decimals=1)})


    # Fetch additional info for yield
    info = fetch_stock_info(symbol) or {}
    yield_val = info.get("dividend_yield")
    formatted_yield = f"{yield_val:.2%}" if yield_val is not None else "データなし"

    yield_info = {
        "yield": formatted_yield,
        "policy": "安定配当を目標（参考値）",
    }
    return {"dividends": rows, "yield_info": yield_info}


def get_shareholder_tab(code: str) -> Dict[str, Any]:
    # 実データがないため、サンプルを返す
    benefit = {
        "min_shares": 100,
        "content": "自社製品クーポンまたはギフトカード",
        "months": "年2回（3月 / 9月）",
        "note": "内容はIRでご確認ください",
    }
    return {"benefit": benefit}


CANDLE_PATTERN_GROUP_COUNTS = {
    # Keep in sync with CANDLE_PATTERN_CARDS.
    "basic": 5,
    "advanced": 9,
}


def get_candle_patterns_page() -> Dict[str, Any]:
    categories = [
        {"key": "陽線", "tone": "bullish"},
        {"key": "陰線", "tone": "bearish"},
        {"key": "迷い", "tone": "neutral"},
    ]
    group_labels = {
        "basic": "単体ローソク（基本編）",
        "advanced": "複数ローソク（応用編）",
    }
    group_by_category: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
        g: {c["key"]: [] for c in categories} for g in group_labels
    }
    for item in CANDLE_PATTERN_CARDS:
        group = item.get("group", "basic")
        category = item.get("category")
        if group in group_by_category and category in group_by_category[group]:
            group_by_category[group][category].append(item)

    category_counts = {
        c["key"]: sum(len(group_by_category[g][c["key"]]) for g in group_by_category) for c in categories
    }
    return {
        "patterns": CANDLE_PATTERN_CARDS,
        "categories": categories,
        "group_by_category": group_by_category,
        "group_labels": group_labels,
        "group_counts": CANDLE_PATTERN_GROUP_COUNTS,
        "category_counts": category_counts,
    }


def get_glossary_terms() -> List[Dict[str, str]]:
    return GLOSSARY_TERMS


def get_timestamp_label() -> str:
    now = datetime.now()
    return now.strftime("(%Y/%m/%d %H:%M 時点)")
