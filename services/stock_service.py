from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from utils.analyzer import (
    add_technical_indicators,
    analyze_candlestick,
    calculate_trendline,
    detect_dead_cross,
    detect_golden_cross,
    get_direction_label,
)
from utils.candle_classify import get_candle_info
from services.data_fetcher import (
    fetch_dividends,
    fetch_realtime_data,
    fetch_stock_data,
    fetch_stock_info,
    format_symbol_for_yfinance,
)
from services.fundamental_fetcher import (
    build_company_scores,
    format_date,
    format_fundamental_value,
    get_event_info,
    get_fundamental_statuses,
    get_key_fundamentals,
)
from data.stock_name_mapper import STOCK_NAME_MAP
from data.terms_data import TERMS_DATA

from services.financial_analyzer import FinancialAnalyzer
from services.jquants_client import client as jquants_client

# アナライザーの初期化
analyzer = FinancialAnalyzer()

# ウォッチリストのサンプル銘柄 (簡易的なインメモリ保存)
_WATCHLIST_CODES = ["7203", "6758", "9984", "8306", "8035"]

def get_watchlist_codes() -> List[str]:
    return _WATCHLIST_CODES

def add_stock_to_watchlist(code: str) -> bool:
    if code not in _WATCHLIST_CODES:
        _WATCHLIST_CODES.append(code)
        return True
    return False

def remove_stocks_from_watchlist(codes: List[str]):
    global _WATCHLIST_CODES
    _WATCHLIST_CODES = [c for c in _WATCHLIST_CODES if c not in codes]

def search_stocks(query: str) -> List[Dict[str, str]]:
    query = query.lower().strip()
    if not query:
        return []
    
    results = []
    
    results = []
    
    # Try fetching from J-Quants
    issues = jquants_client.get_listed_issues()
    if issues:
        # Search in J-Quants data
        for issue in issues:
            code = issue.get("Code", "")
            # Normalize J-Quants V2 5-digit code (e.g. 72030 -> 7203)
            if len(code) == 5 and code.endswith("0"):
                code = code[:4]

            # V2: CoName, V1: CompanyName
            name = issue.get("CoName") or issue.get("CompanyName") or ""
            # V2: CoNameEn, V1: CompanyNameEnglish
            name_en = issue.get("CoNameEn") or issue.get("CompanyNameEnglish") or ""
            
            # 接頭辞一致 (コードまたは名称)
            # ユーザー要件: "前方一致"
            code_match = code.lower().startswith(query)
            name_match = name.lower().startswith(query)
            name_en_match = name_en.lower().startswith(query)

            if code_match or name_match or name_en_match:
                results.append({"code": code, "name": name})
                
            # Note: We need to sort ALL results, so we can't break early easily if we want global sort.
            # But getting ALL matches might be heavy if query is just "1".
            # Let's cap at a higher number then sort? Or just sort all matches.
            # Japanese market has ~4000 stocks. Iterating all is fast in Python.
            
    else:
        # Fallback to static map
        for code, name in STOCK_NAME_MAP.items():
            if code.endswith('.T'):
                continue
                
            # Prefix match
            if code.lower().startswith(query) or name.lower().startswith(query):
                results.append({"code": code, "name": name})

    # Sort results by code (Ascending)
    # Filter duplicates just in case
    unique_results = {r['code']: r for r in results}.values()
    sorted_results = sorted(unique_results, key=lambda x: x['code'])

    return sorted_results[:10]  # Limit results after sorting


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
            # Check for explicit ID mapping or fall back to English name
            english_name = term.get("english") or key
            term_id = english_name.lower().replace(" ", "_")
            
            # Manual overrides for acronyms to match images (per.png, rsi.png etc)
            if key in ["PER", "PBR", "RSI", "MACD"]:
                term_id = key.lower()

            terms.append(
                {
                    "term": term.get("japanese") or key,
                    "meaning": term.get("meaning") or "",
                    "tip": term.get("usage") or "",
                    "category": category,
                    "id": term_id,
                }
            )
    return terms


GLOSSARY_TERMS = _build_glossary_terms()

# ローソク足パターンのカードデータ
CANDLE_PATTERN_CARDS = [
    # Basic Bullish
    {
        "id": "big_bull",
        "name": "大陽線",
        "group": "basic",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/candle_patterns/big_bull.svg",
        "catch": "強い買い圧力が続くサイン",
        "desc_lead": "流れを変える長い陽線",
        "desc_body": "始値から大きく上昇し、実体が長くなる形です。",
        "detail_desc": "材料が出た直後やトレンド転換の初動で現れやすい長い陽線です。出来高が伴えば信頼度が上がります。",
        "scene": "好材料発表直後や強い反発場面",
        "howto": "実体の長さと出来高の増加を確認する",
        "notes": ["出来高が増えているか確認", "翌日の反落に注意"],
    },
    {
        "id": "small_bull",
        "name": "小陽線",
        "group": "basic",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/candle_patterns/small_bull.svg",
        "catch": "小休止、あるいは迷い",
        "desc_lead": "実体の短い陽線",
        "desc_body": "値幅が小さく、買い勢力が限定的な状態です。",
        "detail_desc": "相場の迷いを示します。高値圏で出ると失速、安値圏で出ると底打ちの準備段階となることがあります。",
        "scene": "トレンドの途中や持ち合い局面",
        "howto": "前後の足とのバランスを確認する",
        "notes": ["単体での判断は難しい", "翌日の足で方向性を確認"],
    },
    {
        "id": "upper_shadow_bull",
        "name": "上影陽線",
        "group": "basic",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/candle_patterns/upper_shadow_bull.svg",
        "catch": "上昇したものの売り戻された形",
        "desc_lead": "長い上ヒゲを持つ陽線",
        "desc_body": "一時大きく買われたものの、終値にかけて売り込まれた状態です。",
        "detail_desc": "高値圏で現れると、上昇エネルギーの限界や利益確定売りの強さを示唆します。警戒が必要なサインです。",
        "scene": "上昇トレンドの後半や抵抗線付近",
        "howto": "ヒゲの長さと実体の位置関係を見る",
        "notes": ["高値圏での出現は反落注意", "ヒゲが長いほど売り圧力が強い"],
    },
    {
        "id": "lower_shadow_bull",
        "name": "下影陽線",
        "group": "basic",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/candle_patterns/lower_shadow_bull.svg",
        "catch": "安値から力強く買い戻されたサイン",
        "desc_lead": "長い下ヒゲを持つ陽線",
        "desc_body": "安値まで売られた後、力強く買い戻されて陽線で引けた形です。",
        "detail_desc": "安値圏で出ると強力なサポートの証明となり、底打ち・反発の期待が高まります。ハンマーとも呼ばれます。",
        "scene": "下落トレンドの終盤やサポート付近",
        "howto": "下ヒゲの長さと直近安値を確認",
        "notes": ["安値圏での出現は買いチャンス", "出来高増加を伴うと信頼度アップ"],
    },
    {
        "id": "bozu_bull",
        "name": "寄引坊主（陽）",
        "group": "basic",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/candle_patterns/bozu_bull.svg",
        "catch": "寄りから引けまで買われ続けた極めて強い形",
        "desc_lead": "上下にヒゲがない陽線",
        "desc_body": "安値が始値、高値が終値となる、迷いのない上昇を示します。",
        "detail_desc": "非常に強い買い意欲を示し、翌日以降も続伸する可能性が高いパターンです。トレンド形成の初動によく見られます。",
        "scene": "トレンド転換の初動や急騰場面",
        "howto": "ヒゲが全くないかもしくは極めて短いことを確認",
        "notes": ["非常に強いサイン", "過熱感がないかだけ注意"],
    },

    # Basic Bearish
    {
        "id": "big_bear",
        "name": "大陰線",
        "group": "basic",
        "category": "陰線",
        "tone": "bearish",
        "svg": "images/candle_patterns/big_bear.svg",
        "catch": "強い売りが続くサイン",
        "desc_lead": "流れを変える長い陰線",
        "desc_body": "始値から大きく下落し、実体が長くなる形です。",
        "detail_desc": "悪材料直後やトレンド転換の初動で現れやすい陰線です。出来高が伴えば信頼度が上がります。",
        "scene": "悪材料発表直後や急落局面",
        "howto": "実体の長さと出来高の増加を確認する",
        "notes": ["出来高が増えているか確認", "翌日の自律反発に注意"],
    },
    {
        "id": "small_bear",
        "name": "小陰線",
        "group": "basic",
        "category": "陰線",
        "tone": "bearish",
        "svg": "images/candle_patterns/small_bear.svg",
        "catch": "勢いの衰え、あるいは押し目",
        "desc_lead": "実体の短い陰線",
        "desc_body": "値幅が小さく、売り圧力が限定的な状態です。",
        "detail_desc": "上昇トレンド中の「押し目」や、下落トレンド中の「一服」を示します。次の一手への準備段階です。",
        "scene": "トレンドの途中や持ち合い局面",
        "howto": "前後の足の勢いと比較する",
        "notes": ["強い下落の後の出現は底打ち示唆", "上昇中の出現は健全な調整"],
    },
    {
        "id": "upper_shadow_bear",
        "name": "上影陰線",
        "group": "basic",
        "category": "陰線",
        "tone": "bearish",
        "svg": "images/candle_patterns/upper_shadow_bear.svg",
        "catch": "戻り売りを浴びせられた弱い形",
        "desc_lead": "長い上ヒゲを持つ陰線",
        "desc_body": "上昇しようとしたが強い売りに押され、安値圏で引けた状態です。",
        "detail_desc": "非常に弱い形です。特に高値圏での出現は、上昇トレンドの完全な終焉と戻り売りの強まりを暗示します。",
        "scene": "高値圏での反落や戻り売りの場面",
        "howto": "長い上ヒゲと終値の位置を確認",
        "notes": ["高値圏では逃げ場", "下落加速のサインとなることが多い"],
    },
    {
        "id": "lower_shadow_bear",
        "name": "下影陰線",
        "group": "basic",
        "category": "陰線",
        "tone": "bearish",
        "svg": "images/candle_patterns/lower_shadow_bear.svg",
        "catch": "売られたが買い戻しの形跡あり",
        "desc_lead": "長い下ヒゲを持つ陰線",
        "desc_body": "大きく売られたものの、引けにかけて一定の買い戻しが入った状態です。",
        "detail_desc": "下落の勢いにブレーキがかかったことを示します。安値圏で出ると、下げ止まりの予兆となることがあります。",
        "scene": "下落トレンドの中盤から終盤",
        "howto": "下ヒゲの長さと始値・終値の距離を見る",
        "notes": ["下げ止まりの期待はあるが、翌日の陽線確認が必要"],
    },
    {
        "id": "bozu_bear",
        "name": "寄引坊主（陰）",
        "group": "basic",
        "category": "陰線",
        "tone": "bearish",
        "svg": "images/candle_patterns/bozu_bear.svg",
        "catch": "寄りから引けまで売られ続けた絶望的な形",
        "desc_lead": "上下にヒゲがない陰線",
        "desc_body": "高値が始値、安値が終値となる、一切の買い戻しがない下落です。",
        "detail_desc": "非常に強い売り圧力。悪材料の織り込み不足や、パニック売りの最中に現れます。続落への警戒が必須です。",
        "scene": "急落局面や重要な節目割れ",
        "howto": "ヒゲが全くないことを確認",
        "notes": ["投げ売りが出尽くすまで続く可能性あり", "安値圏での出現は最後の一押しのことも"],
    },

    # Basic Neutral (Doji)
    {
        "id": "doji",
        "name": "十字線",
        "group": "basic",
        "category": "迷い",
        "tone": "neutral",
        "svg": "images/candle_patterns/doji.svg",
        "catch": "売り買いが完全に拮抗した状態",
        "desc_lead": "始値と終値がほぼ等しい",
        "desc_body": "市場が次の方向性を探っている、迷いの極致です。",
        "detail_desc": "トレンドの転換点で現れやすく、特に強い上昇や下落の後に現れるとエネルギーの枯渇を意味します。",
        "scene": "トレンドの終盤、イベント前",
        "howto": "上下のヒゲの長さと実体の薄さを確認",
        "notes": ["単独では判断せず、翌日の足を待つ"],
    },
    {
        "id": "upper_shadow_doji",
        "name": "上影十字（トウバ）",
        "group": "basic",
        "category": "迷い",
        "tone": "neutral",
        "svg": "images/candle_patterns/upper_shadow_doji.svg",
        "catch": "高値で強い売りを浴びた迷い",
        "desc_lead": "長い上ヒゲのある十字線",
        "desc_body": "買われたが元の価格まで押し戻された、天井圏で出やすい形です。",
        "detail_desc": "上昇力の限界を示唆します。墓石とも呼ばれ、高値圏での出現は反落への強い警戒サインとなります。",
        "scene": "上昇トレンドの天井圏",
        "howto": "上ヒゲの長さと終値の位置をチェック",
        "notes": ["高値圏であれば利益確定を検討する水準"],
    },
    {
        "id": "lower_shadow_doji",
        "name": "下影十字（トンボ）",
        "group": "basic",
        "category": "迷い",
        "tone": "neutral",
        "svg": "images/candle_patterns/lower_shadow_doji.svg",
        "catch": "安値で強い買い戻しが入った迷い",
        "desc_lead": "長い下ヒゲのある十字線",
        "desc_body": "売られたが元の価格まで買い戻された、底打ち圏で出やすい形です。",
        "detail_desc": "下落エネルギーが尽き、買いが勝ち始めたサインです。安値圏での出現は反発開始の有力候補です。",
        "scene": "下落トレンドの安値圏",
        "howto": "下ヒゲの長さと始値・終値が一致しているか確認",
        "notes": ["安値圏での出現は買い転換のシグナル"],
    },
    {
        "id": "marubozu_doji",
        "name": "寄引同時線",
        "group": "basic",
        "category": "迷い",
        "tone": "neutral",
        "svg": "images/candle_patterns/marubozu_doji.svg",
        "catch": "取引が極めて少なく、方向感がない",
        "desc_lead": "ヒゲもほとんどない十字",
        "desc_body": "価格変動がほとんどなかった状態です。",
        "detail_desc": "市場の関心が極めて低いか、大きな材料を前に売買が凍り付いている状態。嵐の前の静けさになることも。",
        "scene": "商いが薄い時、重要イベントの直前",
        "howto": "実体とヒゲの短さを確認",
        "notes": ["流動性不足に注意"],
    },
    {
        "id": "dragonfly_doji",
        "name": "トンボ",
        "group": "basic",
        "category": "迷い",
        "tone": "neutral",
        "svg": "images/candle_patterns/dragonfly_doji.svg",
        "catch": "安値で強い買いが入った反落回避サイン",
        "desc_lead": "始値・終値が高値で一致し、長い下ヒゲを持つ",
        "desc_body": "大きく売られたが、引けにかけて寄り付き価格まで一気に買い戻された形。",
        "detail_desc": "安値圏では強い反発サイン、高値圏では転換の予兆となることも。売りを跳ね返した強さを示します。",
        "scene": "下落トレンドの安値圏、サポート付近",
        "howto": "下ヒゲが長く、上ヒゲがないことを確認",
        "notes": ["安値圏では強力な買い場"],
    },
    {
        "id": "gravestone_doji",
        "name": "墓石",
        "group": "basic",
        "category": "迷い",
        "tone": "neutral",
        "svg": "images/candle_patterns/gravestone_doji.svg",
        "catch": "高値で強い売りを浴び、力尽きた形",
        "desc_lead": "始値・終値が安値で一致し、長い上ヒゲを持つ",
        "desc_body": "大きく買われたが、引けにかけて寄り付き価格まで一気に叩き売られた形。",
        "detail_desc": "上昇エネルギーの枯渇を示します。高値圏での出現は、強烈な戻り売りを暗示する反落サインです。",
        "scene": "上昇トレンドの高値圏、抵抗線付近",
        "howto": "上ヒゲが長く、下ヒゲがないことを確認",
        "notes": ["高値圏では即座に警戒"],
    },
    {
        "id": "koma",
        "name": "コマ",
        "group": "basic",
        "category": "迷い",
        "tone": "neutral",
        "svg": "images/candle_patterns/koma.svg",
        "catch": "攻防が続いて膠着した形",
        "desc_lead": "実体もヒゲも短い形",
        "desc_body": "売り買いが小規模な範囲で拮抗しています。",
        "detail_desc": "トレンドの勢いが低下していることを示します。どちらに放れるかのエネルギーを蓄積している段階です。",
        "scene": "保ち合い局面、トレンドの過渡期",
        "howto": "実体の小ささと上下ヒゲのバランスを見る",
        "notes": ["トレンド方向への再度抜けを待つ"],
    },
    {
        "id": "long_legged_doji",
        "name": "足長同時線",
        "group": "basic",
        "category": "迷い",
        "tone": "neutral",
        "svg": "images/candle_patterns/long_legged_doji.svg",
        "catch": "激しい売買が交錯し、結果引き分けた",
        "desc_lead": "上下ヒゲが非常に長い十字",
        "desc_body": "一度大きく変動したが、結局元に戻った激しい迷い。転換の兆しです。",
        "detail_desc": "ボラティリティの急増。相場の大きな転換点になることが多く、翌日の動き出しは順張り推奨される場面です。",
        "scene": "相場の山や谷、過熱圏",
        "howto": "上下ヒゲの長さが際立っているか確認",
        "notes": ["翌日に窓を開けて動き出す場合は要注意"],
    },

    # Advanced 2-Candle
    {
        "id": "bull_engulfing",
        "name": "包み足（陽の包み・抱き線）",
        "group": "advanced",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/candle_patterns/bull_engulfing.svg",
        "catch": "前日の陰線を完全に飲み込む強い買い",
        "desc_lead": "小さな陰線の次に大きな陽線",
        "desc_body": "前日の実体を当日の陽線が完全に包み込む形。",
        "detail_desc": "売りの勢いが完全に屈し、買いが圧倒したことを示す強力な底打ちサインです。出来高を伴うと信頼度マックス。",
        "scene": "安値圏での反転開始",
        "howto": "陽線の実体が前日の陰線実体より大きいことを確認",
        "notes": ["安値圏では絶好の買い場"],
    },
    {
        "id": "bear_engulfing",
        "name": "包み足（陰の包み）",
        "group": "advanced",
        "category": "陰線",
        "tone": "bearish",
        "svg": "images/candle_patterns/bear_engulfing.svg",
        "catch": "上昇を否定する強力な売り",
        "desc_lead": "小さな陽線の次に大きな陰線",
        "desc_body": "前日の実体を当日の陰線が完全に包み込む形。",
        "detail_desc": "買いの勢いが完全に消沈し、売りが主導権を握ったことを示します。高値圏では逃げ場のラストチャンスになることも。",
        "scene": "高値圏での反落開始",
        "howto": "陰線の実体が前日の陽線実体より大きいことを確認",
        "notes": ["高値圏では即座に警戒が必要"],
    },
    {
        "id": "harami",
        "name": "はらみ足",
        "group": "advanced",
        "category": "迷い",
        "tone": "neutral",
        "svg": "images/candle_patterns/harami.svg",
        "catch": "値動きが落ち着き、パワーを蓄積中",
        "desc_lead": "前日の実体内に当日の実体が収まる",
        "desc_body": "前日の大きな動きの後に、値動きが収縮した状態。",
        "detail_desc": "相場が一旦小休止し、次の大きな変動に向けた「孕み」の状態。放れた方向に大きなトレンドが発生しやすいです。",
        "scene": "トレンドの途中、急騰急落のあと",
        "howto": "前日のローソク足の実体内に、今日の足が完全に収まっているか見る",
        "notes": ["どちらに放れるかに注視"],
    },
    {
        "id": "inyo_harami",
        "name": "陰陽はらみ",
        "group": "advanced",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/candle_patterns/bull_bear_harami.svg",
        "catch": "下落が止まり、反発の準備が整った",
        "desc_lead": "陰線の実体内に小さな陽線",
        "desc_body": "大きな下落の後に、小さな陽線が包まれた状態です。",
        "detail_desc": "底打ちを示唆するパターンです。売りの枯渇と買いの慎重な発生を意味し、翌日に窓を開けて上昇し始めると反転が確定します。",
        "scene": "下落の極端な安値圏",
        "howto": "一昨日の大陰線と昨日の小陽線の位置関係を確認",
        "notes": ["翌日に前日の高値を抜ければ買い"],
    },
    {
        "id": "kiriage",
        "name": "切り上げ線",
        "group": "advanced",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/candle_patterns/kiriage.svg",
        "catch": "売りをこなして下値を切り上げた形",
        "desc_lead": "前日の安値を下回らず、高く終わる",
        "desc_body": "安値が前日より高くなり、さらに陽線で引ける形です。",
        "detail_desc": "買い意欲が非常に強く、押し目でも売り切れない勢いを示します。上昇トレンドの持続性が高いことを示唆します。",
        "scene": "上昇トレンド中の押し目完了",
        "howto": "連続する陽線の安値が切り上がっているか確認",
        "notes": ["買い乗せのチャンス"],
    },
    {
        "id": "kirisage",
        "name": "切り下げ線",
        "group": "advanced",
        "category": "陰線",
        "tone": "bearish",
        "svg": "images/candle_patterns/kirisage.svg",
        "catch": "買いを圧倒して上値を切り下げた形",
        "desc_lead": "前日の高値を上回れず、安く終わる",
        "desc_body": "高値が前日より低くなり、さらに陰線で引ける形です。",
        "detail_desc": "戻り売り圧力が強く、買いが続かない状態を示します。下落トレンドが本格化する際によく見られます。",
        "scene": "下落トレンド中の戻り売り局面",
        "howto": "連続する陰線の高値が切り下がっているか確認",
        "notes": ["売り継続의 판단재료"],
    },
    {
        "id": "kabuse",
        "name": "かぶせ線",
        "group": "advanced",
        "category": "陰線",
        "tone": "bearish",
        "svg": "images/candle_patterns/kabuse.svg",
        "catch": "勢い良く始まったが、結局叩き売られた",
        "desc_lead": "前日終値より高く始まり、安値圏で引ける",
        "desc_body": "前日の陽線に対して、窓を開けて高く始まるが、陽線の中心より下まで売られた陰線。",
        "detail_desc": "高値圏での「失速」を示す代表的なパターン. 買いが騙された形になり、ここから反落に転じることが非常に多いです。",
        "scene": "上昇トレンドの天井圏",
        "howto": "陰線の終値が、前日の陽線実体の中央より下にあるか確認",
        "notes": ["天井打ちの有力候補. 早めの撤退を要検討"],
    },
    {
        "id": "sashikomi",
        "name": "差し込み線",
        "group": "advanced",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/candle_patterns/sashikomi.svg",
        "catch": "売りを食い止めて、反撃に転じようとしている",
        "desc_lead": "陰線の内側まで買いが入る",
        "desc_body": "前日の陰線に対して、低い位置から始まるが、陰線の実体の内側に入り込んで終わる陽線。",
        "detail_desc": "底入れの兆しですが、かぶせ線ほどの決定打ではありません。翌日の足がさらにこの陽線の高値を抜けるかが重要です。",
        "scene": "下落トレンドからの反発局面",
        "howto": "陽線の終値が、前日の陰線実体のどこまで食い込んだか確認",
        "notes": ["翌日の続伸確認で信頼度アップ"],
    },
    {
        "id": "kenuki_zoko",
        "name": "毛抜き底",
        "group": "advanced",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/candle_patterns/kenuki_zoko.svg",
        "catch": "同じ安値で二度踏みとどまった鉄板サポート",
        "desc_lead": "二日連続で同じ安値を記録",
        "desc_body": "前日の安値と当日の安値がピッタリ、あるいはほぼ同じ水準で止まった状態。",
        "detail_desc": "その価格帯が強力な支持線であることを示します。反転の信頼性が高く、ダブルボトムの最小構成単位とも言えます。",
        "scene": "重要指標、あるいは節目の価格での攻防",
        "howto": "下ヒゲの先端（安値）が一致しているか確認",
        "notes": ["強力な買いシグナルの一つ"],
    },
    {
        "id": "kenuki_tenjo",
        "name": "毛抜き天井",
        "group": "advanced",
        "category": "陰線",
        "tone": "bearish",
        "svg": "images/candle_patterns/kenuki_tenjo.svg",
        "catch": "同じ高値で二度跳ね返された強力な抵抗",
        "desc_lead": "二日連続で同じ高値を記録",
        "desc_body": "前日の高値と当日の高値が一致し、上値の重さが露呈した状態。",
        "detail_desc": "非常に強いレジスタンス. ここを突破できないという意思が市場に伝わり、失望売りを誘いやすいパターンです。",
        "scene": "上昇トレンドのピーク、重要節目",
        "howto": "上ヒゲの先端（高値）が一致しているか確認",
        "notes": ["利益確定の好機"],
    },
    {
        "id": "daki_bull",
        "name": "抱き線（陽）",
        "group": "advanced",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/candle_patterns/daki_bull.svg",
        "catch": "これまでの下落トレンドを根底から否定する買い",
        "desc_lead": "前日より幅広く、全体を包み込む",
        "desc_body": "前日の陽線を、今日の陰線が完全に包み込む形（包み足と同じ）。",
        "detail_desc": "圧倒的な力の逆転. 下落局面で出た場合は、トレンド転換の爆発的なエネルギーを示します。",
        "scene": "パニック売り直後のリバウンド局面",
        "howto": "今日の陽線が前日の全てを飲み込んでいるか確認",
        "notes": ["出来高が多ければ信頼度が極めて高い"],
    },
    {
        "id": "daki_bear",
        "name": "抱き線（陰）",
        "group": "advanced",
        "category": "陰線",
        "tone": "bearish",
        "svg": "images/candle_patterns/daki_bear.svg",
        "catch": "これまでの上昇を完全に帳消しにする強烈な売り",
        "desc_lead": "前日より幅広く、全体を飲み込む",
        "desc_body": "前日の陽線を、今日の陰線が完全に包み込む形。",
        "detail_desc": "ここからの大幅下落を示唆します。高値圏で発生すると、その後数日間にわたる調整に入るリスクが高いです。",
        "scene": "上昇加速後のピーク、バブルの終焉",
        "howto": "今日の陰線が前日の全てを飲み込んでいるか確認",
        "notes": ["即座にポジション縮小を検討すべき局面"],
    },
    {
        "id": "kaeshi",
        "name": "返し線",
        "group": "advanced",
        "category": "迷い",
        "tone": "neutral",
        "svg": "images/candle_patterns/kaeshi.svg",
        "catch": "一歩進んで一歩下がる拮抗局面",
        "desc_lead": "前日の動きをそのまま打ち消す逆の足",
        "desc_body": "陽線のあとに同じくらいの長さの陰線、あるいはその逆が出る形。",
        "detail_desc": "トレンドの継続性に疑義が生じている状態. エネルギーが分散しており、ここから長いレンジ相場に入る予兆のことも。",
        "scene": "トレンドの中盤、材料待ち",
        "howto": "二日間の値幅と方向がほぼ対称であることを確認",
        "notes": ["確信が持てるまで手出し無用"],
    },
    {
        "id": "kubitsuri",
        "name": "首吊り線",
        "group": "advanced",
        "category": "陰線",
        "tone": "bearish",
        "svg": "images/candle_patterns/kubitsuri.svg",
        "catch": "上昇中に買いが入ったが、最後に支えが消えた",
        "desc_lead": "高値圏で出る下ヒゲの長い形（小陰線）",
        "desc_body": "安値まで売られた後、買い戻されたが陽転できず、高値圏で引けた形。",
        "detail_desc": "形は反転に見えますが、高値圏で出ると「最後に残っていた買いが使い果たされた」と解釈され、翌日から急落するリスクがある不吉な形. ",
        "scene": "上昇トレンドの最終盤、クライマックス",
        "howto": "高値圏で下ヒゲが極端に長い陰線を探す",
        "notes": ["非常に騙されやすいので、翌日の寄り付き注意"],
    },

    # Advanced 3-Candle
    {
        "id": "three_white_soldiers",
        "name": "赤三兵",
        "group": "advanced",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/candle_patterns/three_white_soldiers.svg",
        "catch": "着実な上昇が3回続いた確信の強気",
        "desc_lead": "3本連続の陽線",
        "desc_body": "安値圏から、3日連続で陽線が現れる形. 寄り付きが前日の実体内のことも重要。",
        "detail_desc": "トレンド転換の最も信頼できるシグナルの一つです。力強い上昇相場の幕開けを示し、長期保有に適したエントリーポイントです。",
        "scene": "長い下落トレンドからの反転初動",
        "howto": "3本の陽線が等間隔、かつ徐々に高値を更新しているか確認",
        "notes": ["高値圏で出ると「赤三兵先詰まり」となり反動注意"],
    },
    {
        "id": "three_black_crows",
        "name": "黒三兵（三羽烏）",
        "group": "advanced",
        "category": "陰線",
        "tone": "bearish",
        "svg": "images/candle_patterns/three_black_crows.svg",
        "catch": "3日連続の売り. 売り勢力が完全に制圧した",
        "desc_lead": "3本連続の陰線",
        "desc_body": "高値圏から、3日連続で下値を切り下げる陰線が現れる形。",
        "detail_desc": "上昇トレンドの崩壊. 非常に強い売り抜けを示唆し、ここから本格的な下落トレンドへの雪崩現象が起きやすくなります。",
        "scene": "高値圏での急落、トレンド終了",
        "howto": "3本の陰線が連続し、上ヒゲが短いことを確認",
        "notes": ["下げ止まりを待たず、早めの対応が吉"],
    },
    {
        "id": "morning_star",
        "name": "明けの明星",
        "group": "advanced",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/candle_patterns/morning_star.svg",
        "catch": "暗闇を抜けて新しい太陽が昇る反発サイン",
        "desc_lead": "大陰線→十字（窓空き）→大陽線の3本組",
        "desc_body": "大きく下げた後、底値で十字線を挟み、一気に買い戻される形。",
        "detail_desc": "底打ち反転の王道. 真ん中の足（明星）が窓を開けて下のほうに孤立しているほど、その後の反発力は強くなります。",
        "scene": "大暴落の底、長い調整の終わり",
        "howto": "3本目の陽線が、1本目の陰線実体を半分以上戻しているか見る",
        "notes": ["強力な買い転換点"],
    },
    {
        "id": "evening_star",
        "name": "宵の明星",
        "group": "advanced",
        "category": "陰線",
        "tone": "bearish",
        "svg": "images/candle_patterns/evening_star.svg",
        "catch": "華やかさの中に現れた、終わりの始まり",
        "desc_lead": "大陽線→十字（窓空き）→大陰線の3本組",
        "desc_body": "大きく上げた後、高値で十字線を挟み、一気に売り抜かれる形。",
        "detail_desc": "天井打ちの決定版. 上昇エネルギーがピークに達した直後の急落. ここを逃すと大きな含み損を抱えるリスクが高まります。",
        "scene": "バブル的な上昇のピーク",
        "howto": "3本目の陰線が、1本目の陽線実体を深く飲み込んでいるか確認",
        "notes": ["天井圏の致命的なサイン"],
    },
    {
        "id": "sanbagarasu",
        "name": "三羽烏",
        "group": "advanced",
        "category": "陰線",
        "tone": "bearish",
        "svg": "images/candle_patterns/sanbagarasu.svg",
        "catch": "不吉な3羽の烏. 急落の前触れ",
        "desc_lead": "高値圏での3本連続陰線",
        "desc_body": "赤三兵の逆. 特に、前の足の終値よりも高い寄り付きから、大きく崩れるのが特徴。",
        "detail_desc": "確実な天井. 大きな利益確定売りが出口に殺到している状況を示しています。ここからの下落幅は大きくなりがちです。",
        "scene": "高値圏での連続反落",
        "howto": "2本目、3本目の寄り付きが前日の実体内に食い込んでいるか確認",
        "notes": ["順張りの売りポイント"],
    },
    {
        "id": "sanku_tatakikomi",
        "name": "三空叩き込み",
        "group": "advanced",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/candle_patterns/sanku_tatakikomi.svg",
        "catch": "これ以上ない絶望. そして夜明け前",
        "desc_lead": "窓（空）を3回開けて暴落",
        "desc_body": "窓を開けて4本の陰線が連続して並ぶ. 売りの最終段階です。",
        "detail_desc": "酒田五法の一つ. パニック売りの極限. ここからは売る材料がなくなり、あとはリバウンドを待つだけの「買い下がり」推奨場面です。",
        "scene": "異常なまでの急落相場",
        "howto": "3つの「窓」が明確に存在するか確認",
        "notes": ["逆張り買いの最高峰だが、リスクも高い"],
    },
    {
        "id": "rising_three_methods",
        "name": "上げ三法",
        "group": "advanced",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/candle_patterns/rising_three_methods.svg",
        "catch": "上昇を続けるための健全な休憩（押し目買い）",
        "desc_lead": "大陽線のなかの小さな3本（中休み）",
        "desc_body": "大陽線のあとに小さな陰線が3本続き、再度大陽線で上抜ける形。",
        "detail_desc": "上昇トレンド継続の最強パターン. 調整が前日の大陽線実体内で終わる限り、上昇エネルギーは温存されています。",
        "scene": "強い上昇トレンドの中休み",
        "howto": "中央の小足が大陽線の実体内に収まっているか確認",
        "notes": ["再度の上抜けで買い増し"],
    },
    {
        "id": "falling_three_methods",
        "name": "下げ三法",
        "group": "advanced",
        "category": "陰線",
        "tone": "bearish",
        "svg": "images/candle_patterns/falling_three_methods.svg",
        "catch": "下落がさらに深まる前の絶望的な戻り売り",
        "desc_lead": "大陰線のなかの小さな3本（中休み）",
        "desc_body": "大陰線のあとに小さな陽線が3本続き、再度大陰線で下抜ける形。",
        "detail_desc": "下落トレンド継続. リバウンドがあまりにも弱く、再び売りが再開されることを確信に変えるパターンです。",
        "scene": "強い下落トレンドの中休み",
        "howto": "中央ের小足が大陰線の実体内に収まっているか確認",
        "notes": ["再度の下抜けで空売りチャンス"],
    },
    {
        "id": "sutego",
        "name": "捨て子線",
        "group": "advanced",
        "category": "迷い",
        "tone": "neutral",
        "svg": "images/candle_patterns/sutego.svg",
        "catch": "完全に孤立した十字線. 強力な転換点",
        "desc_lead": "上下に窓（空）を開けた十字線",
        "desc_body": "前後の足と全く連結していない、ポツンと離れた十字。",
        "detail_desc": "これまでの勢いとの「断絶」. 底打ち・天井打ちの可能性が極めて高い、非常に希少で、かつ信頼性の高いシグナルです。",
        "scene": "相場のクライマックス、トレンド転換の大本命",
        "howto": "真ん中の十字線のヒゲすら、前後の足と重ならないことを確認",
        "notes": ["滅多に出ないが、出たら非常に重要"],
    },
    {
        "id": "sanpei_hasami",
        "name": "三兵挟み",
        "group": "advanced",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/candle_patterns/sanpei_hasami.svg",
        "catch": "上昇中に小休止したが、まだ強気継続",
        "desc_lead": "陽線の間に1本だけ陰線を挟む",
        "desc_body": "陽・陰・陽の並びだが、真ん中の陰腺が小さく、上昇の流れを壊さない。",
        "detail_desc": "利益確定売りを十分にこなしながら上昇している健康的な形. 急騰しすぎず、息の長い上昇トレンドになりやすいです。",
        "scene": "緩やかな上昇トレンドの途中",
        "howto": "陰線を次の陽線ですぐに上書き（包み込む）するか見る",
        "notes": ["押し目拾いに最適"],
    },
    {
        "id": "gyaku_sanzon",
        "name": "逆三尊型（三本構成イメージ）",
        "group": "advanced",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/candle_patterns/gyaku_sanzon.svg",
        "catch": "これ以上は下がらないという強固な底値形成",
        "desc_lead": "3つの谷を作るチャート形状",
        "desc_body": "左肩、頭（中央最安値）、右肩を形成して、ネックラインを抜ける。",
        "detail_desc": "底入れの最も有名な形. ここでは簡略化して見せますが、大規模な転換点として、大口投資家も重視する最重要ポイントです。",
        "scene": "大底圏での大がかりな地固め",
        "howto": "中央が最も低く、左右の谷が揃っているか確認",
        "notes": ["ネックライン突破が買いの号令"],
    },
    {
        "id": "harami_sanbon",
        "name": "はらみ三本",
        "group": "advanced",
        "category": "迷い",
        "tone": "neutral",
        "svg": "images/candle_patterns/harami_sanbon.svg",
        "catch": "はらみ足のあとに放れた、本格始動の合図",
        "desc_lead": "はらみの後に、前々日の実体を抜ける足が出る",
        "desc_body": "二日間の「はらみ」状態から、三日目の足がレンジを抜けていく形。",
        "detail_desc": "はらみ足によるエネルギー蓄積が終わり、トレンドが動き出したことを示します。抜けた方向に付いていくのが基本です。",
        "scene": "保ち合いの最終局面",
        "howto": "三日目の足が、初日の大足の高値を抜けるか安値を割るかを確認",
        "notes": ["トレンド再開の強いサイン"],
    },
    {
        "id": "island_reversal",
        "name": "アイランドリバーサル",
        "group": "advanced",
        "category": "迷い",
        "tone": "neutral",
        "svg": "images/candle_patterns/island_reversal.svg",
        "catch": "孤島に閉じ込められた価格帯. 強い逆行のサイン",
        "desc_lead": "窓と窓に挟まれた取り残されたエリア",
        "desc_body": "窓を開けて下げた後、しばらく横ばい、そしてさらに窓を開けて上げる（逆も然り）。",
        "detail_desc": "市場参加者の「総入れ替え」が起きた印. 窓の価格帯には誰もいないため、強力な支持や抵抗として機能し続けます. ",
        "scene": "急激な流れの変化、ニュースによる反落反騰",
        "howto": "「窓」によって他のロウソク足と切り離された塊を探す",
        "notes": ["放れた方向に追随するのが鉄則"],
    },
    {
        "id": "sanzan",
        "name": "三山（三尊簡易形）",
        "group": "advanced",
        "category": "陰線",
        "tone": "bearish",
        "svg": "images/candle_patterns/sanzan.svg",
        "catch": "三度の挑戦を退けられた、決定的な天井",
        "desc_lead": "3つの山を形成するチャート形状",
        "desc_body": "高値で3回跳ね返され、ネックラインを割り込む形。",
        "detail_desc": "天井圏形成の最も有名な形の一つ. 逆三尊の逆で、非常に強い売り圧力を示唆します. 長期的な下落局面への入り口です。",
        "scene": "上昇トレンドの大天井",
        "howto": "3本の山が形成され、その後安値を割り込むか見る",
        "notes": ["ダブルトップより大規模な転換点"],
    },

    # Reference Patterns (Windows/Gaps)
    {
        "id": "gap_up",
        "name": "窓開け（ギャップアップ）",
        "group": "advanced",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/candle_patterns/gap_up.svg",
        "catch": "好材料により買いが殺到している状態",
        "desc_lead": "前日高値よりも高く寄り付く",
        "desc_body": "前日の価格帯と全く重ならない高い位置から取引が始まること。",
        "detail_desc": "需要が供給を圧倒的に上回っている証拠. 強い材料（決算等）があった際に出やすく、トレンド加速の強力なエネルギーです。",
        "scene": "好決算発表翌日、新サービス発表後",
        "howto": "前日の高値と今日の安値に「空白」があるか確認",
        "notes": ["窓が大きすぎる場合は戻り売りに注意"],
    },
    {
        "id": "gap_down",
        "name": "窓開け（ギャップダウン）",
        "group": "advanced",
        "category": "陰線",
        "tone": "bearish",
        "svg": "images/candle_patterns/gap_down.svg",
        "catch": "悪材料により売りが殺到、パニック気味",
        "desc_lead": "前日安値よりも低く寄り付く",
        "desc_body": "前日の価格帯と連結せず、低く引き離されて取引が始まること。",
        "detail_desc": "失望売りの集中. 心理的な節目を窓で割ると、その後長期的な低迷期に入る「ブレイクaway・ギャップ」になる恐れも. ",
        "scene": "下方修正、不祥事、地政学リスクの顕在化",
        "howto": "前日の安値と今日の高値に「空白」があるか確認",
        "notes": ["リバウンド狙いは危険、落ち着くまで静観"],
    },
    {
        "id": "gap_fill",
        "name": "窓埋め",
        "group": "advanced",
        "category": "迷い",
        "tone": "neutral",
        "svg": "images/candle_patterns/gap_fill.svg",
        "catch": "過熱感が落ち着き、均衡が戻る動き",
        "desc_lead": "開いた窓を埋めるように価格が戻る",
        "desc_body": "窓が開いたあとに、その空白となっていた価格帯を埋める動き。",
        "detail_desc": "「窓は必ず埋まる」という相場格言がありますが、現実は窓埋め後に再びトレンド方向に戻ることが多く、絶好の押し目・戻り売りポイントです. ",
        "scene": "急騰・急落後の自律調整局面",
        "howto": "窓の部分まで株価がタッチしたかを確認",
        "notes": ["窓を埋めたあとの反転が本格トレンド"],
    },
    {
        "id": "madokan_sanpou",
        "name": "窓空け三法",
        "group": "advanced",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/candle_patterns/madokan_sanpou.svg",
        "catch": "窓を開けた勢いを削がず、さらに加速する",
        "desc_lead": "窓開けのあと、中休みを経て再始動",
        "desc_body": "窓を開けた大陽線のあと、窓を埋めずに小休止し、再度上放れる形。",
        "detail_desc": "酒田五法の応用. 窓を開けるほどのエネルギーが本物であることを証明する形です。長期の上昇トレンドにつながりやすいです。",
        "scene": "大相場の初動から中盤",
        "howto": "窓が埋まらなかったことを確認し、再度の高値更新を狙う",
        "notes": ["最強の上昇パターンの一つ"],
    },
    {
        "id": "sakata_gohou",
        "name": "酒田五法（代表形）",
        "group": "advanced",
        "category": "迷い",
        "tone": "neutral",
        "svg": "images/candle_patterns/sakata_gohou.svg",
        "catch": "相場の心理を極める江戸時代の英知",
        "desc_lead": "三山・三川・三空・三兵・三法の総称",
        "desc_body": "日本発祥のローソク足分析の原点. 市場の熱狂と絶望を読み解きます。",
        "detail_desc": "単なる図形ではなく、市場参加者の心理状態を把握するための哲学です。すべてのロウソク足分析の基礎となります。",
        "scene": "あらゆる局面で参照される基本概念",
        "howto": "それぞれの代表的な形を複合的に判断する",
        "notes": ["江戸時代の米相場から続く普遍的な知恵"],
    },
    {
        "id": "range_break",
        "name": "レンジブレイク型",
        "group": "advanced",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/candle_patterns/range_break.svg",
        "catch": "溜めに溜めたエネルギーが爆発した瞬間",
        "desc_lead": "持ち合いを力強い一本が突き抜ける",
        "desc_body": "長期間続いた一定の価格帯（レンジ）を、大陽線や窓で上抜けること。",
        "detail_desc": "売り手と買い手の均衡が崩れたシグナル. レンジの期間が長いほど、その後の上昇（または下落）の幅は大きくなります。順張りのチャンス。",
        "scene": "長いボックス圏を抜けて新高値を取る時",
        "howto": "これまでの抵抗線を突き抜けたことを確認",
        "notes": ["騙しを避けるため出来高の増加をチェック"],
    },
    {
        "id": "volume_window",
        "name": "出来高伴う窓形成",
        "group": "advanced",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/candle_patterns/volume_window.svg",
        "catch": "大口の買いが入り、トレンドが本物だと確信",
        "desc_lead": "窓開けと同時に出来高が急増",
        "desc_body": "窓が開くと同時に、普段の数倍の売買が行われた状態。",
        "detail_desc": "単なる窓よりもはるかに信頼度が高いです。機関投資家や大口の意志が反映されており、この窓が埋まるには相当の悪材料が必要になります。",
        "scene": "サプライズ決算へのポジティブ反応",
        "howto": "窓の大きさと共に、下の出来高バーの高さに注目",
        "notes": ["上昇トレンドの最良のエントリーポイント"],
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
    label = get_direction_label(closes, positive_label="トレンド相場：上昇", negative_label="トレンド相場：下落", neutral_label="レンジ相場：もみ合い")
    return label


def _trend_description(label: str) -> str:
    if "上昇" in label:
        return "高値・安値を切り上げながら上昇している状態です。買い優勢の局面です。"
    elif "下落" in label:
        return "高値・安値を切り下げながら下落している状態です。売り優勢の局面です。"
    elif "もみ合い" in label:
        return "一定の範囲内で価格が上下している状態です。方向感が乏しい局面です。"
    return "トレンドの方向性が明確ではありません。"


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
    for code in get_watchlist_codes():
        symbol = format_symbol_for_yfinance(code)
        info = fetch_stock_info(symbol) or {}
        display_name = _jp_name(code, info.get("name"))
        history = fetch_stock_data(symbol, period="1mo", interval="1d")
        high_low_text = "N/A"
        if history is not None and not history.empty:
            high_val = float(history["high"].max())
            low_val = float(history["low"].min())
            high_low_text = f"{math.floor(high_val):,} / {math.floor(low_val):,}"

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
    
    # 単純移動平均 (SMA) の計算
    sma_periods = [25, 75, 200]  # 日足のデフォルト
    if interval == "1wk":
        sma_periods = [13, 26, 52]
    elif interval == "1mo":
        sma_periods = [12, 24, 60]
    elif interval in INTRADAY_INTERVALS:
        sma_periods = [] # イントラデイ（日中足）では今のところSMAを表示しない、あるいは短い期間を使用する
    
    if df is not None and not df.empty and sma_periods:
        df = add_technical_indicators(df, sma_periods=sma_periods)

    points = _build_points(df if df is not None else pd.DataFrame(), interval)
    support_levels = _support_levels(points)
    support_levels = _support_levels(points)
    trend_label = _trend_label(points)
    trend_desc = _trend_description(trend_label)
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
        "chart_summary": chart_summary,
        "trend_label": trend_label,
        "trend_desc": trend_desc,
        "chart_payload": {"points": points, "support_levels": support_levels},
        "chart_payload": {"points": points, "support_levels": support_levels},
        "support_levels": support_levels,
        "signals": signals,
        "risks": risks,
        "positives": positives,
        "axis_note": axis_note,
    }


def get_fundamental_tab(code: str) -> Dict[str, Any]:
    # 1. 既存UIコンポーネント用の元データ (Yahoo Financeベース) を取得
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
    # 1.5 動的なリスク・ポジティブ要素計算のためにチャートデータを取得
    # 標準的なボラティリティ分析のために6ヶ月分の日足データを使用
    chart_df = fetch_stock_data(symbol, period="6mo", interval="1d")
    points = _build_points(chart_df, "1d")
    
    # リスクとポジティブ要素を動的に計算
    # Note: info変数は既に 'fundamental' 辞書として取得されているが、_build_risks は yfinance の info 構造（volume等）を期待している
    # 正確な出来高のために、最新のリアルタイム情報を取得する。
    realtime_info = fetch_realtime_data(symbol) or {}
    risks = _build_risks(points, realtime_info)
    
    # 2. 新しいEDINET分析データを取得
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


    # 利回りの追加情報を取得
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
    "basic": 18,
    "advanced": 35,
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
