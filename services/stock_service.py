from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from models import stock as stock_model
import logging

logger = logging.getLogger(__name__)

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
    fetch_dividend_details,
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

def get_watchlist_codes(db: Session) -> List[str]:
    try:
        stocks = db.query(stock_model.Stock).all()
        return [s.code for s in stocks]
    except Exception as e:
        logger.error(f"Error fetching watchlist: {e}")
        return []

def add_stock_to_watchlist(db: Session, code: str) -> bool:
    try:
        existing = db.query(stock_model.Stock).filter(stock_model.Stock.code == code).first()
        if existing:
            return False
        new_stock = stock_model.Stock(code=code)
        db.add(new_stock)
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Error adding stock {code}: {e}")
        db.rollback()
        return False

def remove_stocks_from_watchlist(db: Session, codes: List[str]):
    try:
        db.query(stock_model.Stock).filter(stock_model.Stock.code.in_(codes)).delete(synchronize_session=False)
        db.commit()
    except Exception as e:
        logger.error(f"Error removing stocks {codes}: {e}")
        db.rollback()

def search_stocks(query: str) -> List[Dict[str, str]]:
    query = query.lower().strip()
    if not query:
        return []
    
    results = []
    
    # Use Stock Master Service for DB-based search
    from services.stock_master_service import stock_master_service
    return stock_master_service.search_stocks(query)


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
        "id": "marubozu_bull",
        "name": "丸坊主",
        "group": "basic",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/candle_patterns/marubozu_bull.svg",
        "action": "強気買い（続伸を狙う）",
        "tips": ["上下にヒゲがない陽線は、始値から終値まで一方的に買われた極めて強い形です。", "大陽線の一種であり、翌日も上昇する可能性が高いです。"],
        "desc_lead": "上下にヒゲがない陽線",
        "desc_body": "始値が安値、終値が高値となる、迷いのない上昇。",
        "detail_desc": "大陽線の一種。非常に強い買い意欲を示し、トレンド形成の初動によく見られます。",
        "scene": "トレンド転換の初動や急騰場面",
        "howto": "ヒゲが全くないことを確認",
    },
    {
        "id": "closing_marubozu_bull",
        "name": "大引け坊主",
        "group": "basic",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/candle_patterns/closing_marubozu_bull.svg",
        "action": "買い（高値引けを確認してエントリー）",
        "tips": ["上ヒゲがない陽線は、引けにかけて買いの勢いが衰えなかったことを示します。", "大陽線の一種であり、強い上昇圧力が継続しています。"],
        "desc_lead": "上ヒゲがない陽線",
        "desc_body": "高値で引けた形。相場がさらに上昇する可能性を示唆する。",
        "detail_desc": "大陽線の一種。引け際まで買いが強かったことを示し、翌日のギャップアップも期待できます。",
        "scene": "上昇トレンド中、好材料",
        "howto": "上ヒゲがないことを確認",
    },
    {
        "id": "opening_marubozu_bull",
        "name": "寄付き坊主",
        "group": "basic",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/candle_patterns/opening_marubozu_bull.svg",
        "action": "買い（押し目買い）",
        "tips": ["下ヒゲがない陽線は、寄り付きから一度も始値を割らずに上昇した形です。", "大陽線の一種であり、始値が強力なサポートとして意識されています。"],
        "desc_lead": "下ヒゲがない陽線",
        "desc_body": "始値が安値で、そこから上昇した形。強い買い意欲を反映している。",
        "detail_desc": "大陽線の一種。寄り付きからの買い意欲が強く、地合いの良さを示唆します。",
        "scene": "底値圏からの反発",
        "howto": "下ヒゲがないことを確認",
    },
    {
        "id": "karakasa_bull",
        "name": "カラカサ",
        "group": "basic",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/candle_patterns/karakasa_bull.svg",
        "action": "買い（底打ちを確認してエントリー）",
        "tips": ["実体が小さく下ヒゲが長い陽線は、安値圏で出ると強力な反発サインです。", "下影陽線の一種であり、売り圧力を跳ね返した証拠です。"],
        "desc_lead": "実体が小さく下ヒゲが長い陽線",
        "desc_body": "大きく売られたが、始値を超えて引けた形。",
        "detail_desc": "下影陽線の一種。安値圏での出現は、底打ち・トレンド転換の非常に有力なシグナルです。",
        "scene": "下落トレンドの底値圏",
        "howto": "実体が小さく、下ヒゲが実体の2倍以上あるか確認",
    },
    {
        "id": "tonkachi_bull",
        "name": "トンカチ",
        "group": "basic",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/candle_patterns/tonkachi_bull.svg",
        "action": "警戒（上値の重さを確認）",
        "tips": ["実体が小さく上ヒゲが長い陽線は、上昇しようとしたが押し戻された形です。", "上影陽線の一種であり、高値圏では天井打ちの懸念があります。"],
        "desc_lead": "実体が小さく上ヒゲが長い陽線",
        "desc_body": "大きく買われたが、終値にかけて押し戻された形。",
        "detail_desc": "上影陽線の一種。高値圏では売り圧力の強まりを示唆し、調整局面入りの可能性があります。",
        "scene": "上昇トレンドの天井圏",
        "howto": "実体が小さく、上ヒゲが実体の2倍以上あるか確認",
    },
    {
        "id": "small_bull",
        "name": "小陽線",
        "group": "basic",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/candle_patterns/small_bull.svg",
        "action": "様子見（次の一手を待つ）",
        "tips": ["価格帯により意味が変わるため、翌日のローソク足がどちらに放れるかを確認してから動きましょう。", "安値圏であれば下げ止まりの予兆、高値圏であれば失速の懸念があります。"],
        "desc_lead": "実体の短い陽線",
        "desc_body": "値幅が小さく、買い勢力が限定的な状態です。",
        "detail_desc": "相場の迷いを示します。高値圏で出ると失速、安値圏で出ると底打ちの準備段階となることがあります。",
        "scene": "トレンドの途中や持ち合い局面",
        "howto": "前後の足とのバランスを確認する",
    },

    # Basic Bearish
    {
        "id": "marubozu_bear",
        "name": "丸坊主",
        "group": "basic",
        "category": "陰線",
        "tone": "bearish",
        "svg": "images/candle_patterns/marubozu_bear.svg",
        "action": "売り（続落を警戒）",
        "tips": ["上下にヒゲがない陰線は、始値から終値まで一方的に売られた極めて弱い形です。", "大陰線の一種であり、翌日も下落する可能性が高いです。"],
        "desc_lead": "上下にヒゲがない陰線",
        "desc_body": "始値が高値、終値が安値となる、迷いのない下落。",
        "detail_desc": "大陰線の一種。非常に強い売り圧力。悪材料の織り込み不足や、パニック売りの最中に現れます。",
        "scene": "急落局面や重要な節目割れ",
        "howto": "ヒゲが全くないことを確認",
    },
    {
        "id": "closing_marubozu_bear",
        "name": "大引け坊主",
        "group": "basic",
        "category": "陰線",
        "tone": "bearish",
        "svg": "images/candle_patterns/closing_marubozu_bear.svg",
        "action": "売り（安値引けを確認して追随）",
        "tips": ["下ヒゲがない陰線は、引けにかけて売りが止まらなかったことを示します。", "大陰線の一種であり、下落圧力が依然として強いです。"],
        "desc_lead": "下ヒゲがない陰線",
        "desc_body": "安値で引けた形。相場がさらに下落する可能性を示唆する。",
        "detail_desc": "大陰線の一種。買い戻しが入らずに終わったため、翌日のギャップダウンも警戒が必要です。",
        "scene": "下落トレンド中",
        "howto": "下ヒゲがないことを確認",
    },
    {
        "id": "opening_marubozu_bear",
        "name": "寄付き坊主",
        "group": "basic",
        "category": "陰線",
        "tone": "bearish",
        "svg": "images/candle_patterns/opening_marubozu_bear.svg",
        "action": "売り（戻り売り）",
        "tips": ["上ヒゲがない陰線は、寄り付きから一度も始値を超えられずに下落した形です。", "大陰線の一種であり、始値が強力なレジスタンスとなっています。"],
        "desc_lead": "上ヒゲがない陰線",
        "desc_body": "始値が高値で、そこから下落した形。強い売り圧力を反映している。",
        "detail_desc": "大陰線の一種。寄り付きからの売り圧力が強く、戻りを試す力もなかったことを示します。",
        "scene": "天井圏からの反落",
        "howto": "上ヒゲがないことを確認",
    },
    {
        "id": "karakasa_bear",
        "name": "カラカサ",
        "group": "basic",
        "category": "陰線",
        "tone": "bearish",
        "svg": "images/candle_patterns/karakasa_bear.svg",
        "action": "様子見（首吊り線に注意）",
        "tips": ["実体が小さく下ヒゲが長い陰線です。安値圏なら反発の兆しですが、高値圏では「首吊り線」となり急落の合図です。", "下影陰線の一種です。出現場所により意味が逆転するため注意が必要です。"],
        "desc_lead": "実体が小さく下ヒゲが長い陰線",
        "desc_body": "売られた後に戻したが、始値には届かなかった形。",
        "detail_desc": "下影陰線の一種。安値圏では買い戻しの兆しかもしれませんが、高値圏では「首吊り足」として非常に危険なサインです。",
        "scene": "高値圏（危険）、安値圏（反発期待）",
        "howto": "実体が小さく、下ヒゲが実体の2倍以上あるか確認",
    },
    {
        "id": "tonkachi_bear",
        "name": "トンカチ",
        "group": "basic",
        "category": "陰線",
        "tone": "bearish",
        "svg": "images/candle_patterns/tonkachi_bear.svg",
        "action": "売り（戻り売り失敗を確認して売り）",
        "tips": ["実体が小さく上ヒゲが長い陰線は、上昇の試みが完全に否定された形です。", "上影陰線の一種であり、非常に弱い形です。"],
        "desc_lead": "実体が小さく上ヒゲが長い陰線",
        "desc_body": "上昇しようとしたが売りに押され、始値より安く引けた形。",
        "detail_desc": "上影陰線の一種。戻り売り圧力が非常に強く、ここから下落トレンドが加速する可能性があります。",
        "scene": "戻り売りの局面、天井圏",
        "howto": "実体が小さく、上ヒゲが実体の2倍以上あるか確認",
    },
    {
        "id": "small_bear",
        "name": "小陰線",
        "group": "basic",
        "category": "陰線",
        "tone": "bearish",
        "svg": "images/candle_patterns/small_bear.svg",
        "action": "様子見（下げ止まりを待つ）",
        "tips": ["下落トレンド中の出現は底打ちの予兆になることがあるため、翌日の陽線出現を待ってから判断してください。", "上昇トレンド中の場合は、健全な押し目となる可能性があります。"],
        "desc_lead": "実体の短い陰線",
        "desc_body": "値幅が小さく、売り圧力が限定的な状態です。",
        "detail_desc": "上昇トレンド中の「押し目」や、下落トレンド中の「一服」を示します。次の一手への準備段階です。",
        "scene": "トレンドの途中や持ち合い局面",
        "howto": "前後の足の勢いと比較する",
    },
    # Basic Neutral (Doji)
    {
        "id": "doji",
        "name": "十字線",
        "group": "basic",
        "category": "迷い",
        "tone": "neutral",
        "svg": "images/candle_patterns/doji.svg",
        "action": "様子見（放れを待って順張り）",
        "tips": ["売り手と買い手の勢力が均衡しており、相場の転換点になりやすい形です。", "翌日のローソク足が前日の高値を抜けるか、安値を割るかを確認してからエントリーしてください。"],
        "desc_lead": "始値と終値がほぼ等しい",
        "desc_body": "市場が次の方向性を探っている、迷いの極致です。",
        "detail_desc": "トレンドの転換点で現れやすく、特に強い上昇や下落の後に現れるとエネルギーの枯渇を意味します。",
        "scene": "トレンドの終盤、イベント前",
        "howto": "上下のヒゲの長さと実体の薄さを確認",
    },
    {
        "id": "upper_shadow_doji",
        "name": "上影十字（トウバ）",
        "group": "basic",
        "category": "迷い",
        "tone": "neutral",
        "svg": "images/candle_patterns/upper_shadow_doji.svg",
        "action": "売り警戒（反落を待って利確）",
        "tips": ["上昇力の限界を示しています。高値圏で出現した場合、翌日に安値を割り込む動きがあれば反落のシグナルとなります。", "「墓石」とも呼ばれ、ここを頂点にトレンドが変わることが多い形です。"],
        "desc_lead": "長い上ヒゲのある十字線",
        "desc_body": "買われたが元の価格まで押し戻された、天井圏で出やすい形です。",
        "detail_desc": "上昇力の限界を示唆します。墓石とも呼ばれ、高値圏での出現は反落への強い警戒サインとなります。",
        "scene": "上昇トレンドの天井圏",
        "howto": "上ヒゲの長さと終値の位置をチェック",
    },
    {
        "id": "lower_shadow_doji",
        "name": "下影十字（トンボ）",
        "group": "basic",
        "category": "迷い",
        "tone": "neutral",
        "svg": "images/candle_patterns/lower_shadow_doji.svg",
        "action": "買い検討（反転の陽線を待つ）",
        "tips": ["強力な下支えがあることを示しています。安値圏で出た場合、翌日に陽線が出現すれば底打ちが確定しやすくなります。", "トレンドの底を見極める重要なサインです。"],
        "desc_lead": "長い下ヒゲのある十字線",
        "desc_body": "売られたが元の価格まで買い戻された、底打ち圏で出やすい形です。",
        "detail_desc": "下落エネルギーが尽き、買いが勝ち始めたサインです。安値圏での出現は反発開始の有力候補です。",
        "scene": "下落トレンドの安値圏",
        "howto": "下ヒゲの長さと始値・終値が一致しているか確認",
    },
    {
        "id": "marubozu_doji",
        "name": "寄引同時線",
        "group": "basic",
        "category": "迷い",
        "tone": "neutral",
        "svg": "images/candle_patterns/marubozu_doji.svg",
        "action": "様子見（商いの増加を待つ）",
        "tips": ["出来高が極端に少ないか、大きな材料待ちの状態です。無理に手を出さず、大きな陽線または陰線が出て動き出すのを待ちましょう。", "流動性が低い銘柄では頻出するため注意が必要です。"],
        "desc_lead": "ヒゲもほとんどない十字",
        "desc_body": "価格変動がほとんどなかった状態です。",
        "detail_desc": "市場の関心が極めて低いか、大きな材料を前に売買が凍り付いている状態。嵐の前の静けさになることも。",
        "scene": "商いが薄い時、重要イベントの直前",
        "howto": "実体とヒゲの短さを確認",
    },
    {
        "id": "dragonfly_doji",
        "name": "トンボ",
        "group": "basic",
        "category": "迷い",
        "tone": "neutral",
        "svg": "images/candle_patterns/dragonfly_doji.svg",
        "action": "買い検討（下値の堅さを確認してエントリー）",
        "tips": ["安値圏では非常に強力な反発サインです。寄り付き価格を維持している限り、強気の姿勢を保てます。", "翌日に窓を開けて上昇すれば、本格的な反騰の合図となります。"],
        "desc_lead": "始値・終値が高値で一致し、長い下ヒゲを持つ",
        "desc_body": "大きく売られたが、引けにかけて寄り付き価格まで一気に買い戻された形。",
        "detail_desc": "安値圏では強い反発サイン、高値圏では転換の予兆となることも。売りを跳ね返した強さを示します。",
        "scene": "下落トレンドの安値圏、サポート付近",
        "howto": "下ヒゲが長く、上ヒゲがないことを確認",
    },
    {
        "id": "gravestone_doji",
        "name": "墓石",
        "group": "basic",
        "category": "迷い",
        "tone": "neutral",
        "svg": "images/candle_patterns/gravestone_doji.svg",
        "action": "即時売り（天井圏での急落に備える）",
        "tips": ["上昇エネルギーが完全に枯渇した状態です。高値圏でこの形が出たら、欲をかかずに一度ポジションを外すことを強く検討してください。", "翌日の続落を待つと逃げ遅れるリスクがあります。"],
        "desc_lead": "始値・終値が安値で一致し、長い上ヒゲを持つ",
        "desc_body": "大きく買われたが、引けにかけて寄り付き価格まで一気に叩き売られた形。",
        "detail_desc": "上昇エネルギーの枯渇を示します。高値圏での出現は、強烈な戻り売りを暗示する反落サインです。",
        "scene": "上昇トレンドの高値圏、抵抗線付近",
        "howto": "上ヒゲが長く、下ヒゲがないことを確認",
    },
    {
        "id": "koma",
        "name": "コマ",
        "group": "basic",
        "category": "迷い",
        "tone": "neutral",
        "svg": "images/candle_patterns/koma.svg",
        "action": "様子見（レンジを上抜けるまで待ち）",
        "tips": ["エネルギー蓄積の段階です。現在のレンジをどちらに大きく放れるかを確認するまで、不用意な売買は避けるのが賢明です。", "トレンドの途中で出た場合は、中休みの可能性があります。"],
        "desc_lead": "実体もヒゲも短い形",
        "desc_body": "売り買いが小規模な範囲で拮抗しています。",
        "detail_desc": "トレンドの勢いが低下していることを示します。どちらに放れるかのエネルギーを蓄積している段階です。",
        "scene": "保ち合い局面、トレンドの過渡期",
        "howto": "実体の小ささと上下ヒゲのバランスを見る",
    },
    {
        "id": "long_legged_doji",
        "name": "足長同時線",
        "group": "basic",
        "category": "迷い",
        "tone": "neutral",
        "svg": "images/candle_patterns/long_legged_doji.svg",
        "action": "注意（大荒れの後の放れを待って順張り）",
        "tips": ["相場が非常に不安定な状態です。高値圏や安値圏で出た場合、翌日に大きく窓を開けて動き出した方向に付いていくのが基本です。", "ヒゲの範囲内は「嵐の目」であり、手を出さないのが無難です。"],
        "desc_lead": "上下ヒゲが非常に長い十字",
        "desc_body": "一度大きく変動したが、結局元に戻った激しい迷い。転換の兆しです。",
        "detail_desc": "ボラティリティの急増。相場の大きな転換点になることが多く、翌日の動き出しは順張り推奨される場面です。",
        "scene": "相場の山や谷、過熱圏",
        "howto": "上下ヒゲの長さが際立っているか確認",
    },

    # Advanced 2-Candle
    {
        "id": "bull_engulfing",
        "name": "包み足（陽の包み・抱き線）",
        "group": "advanced",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/candle_patterns/bull_engulfing.svg",
        "action": "買い（前日高値を抜けてからエントリー）",
        "tips": ["前日の陰線を完全に飲み込む陽線は、強力な反転サインです。安値圏で出た場合、翌日の寄り付きが陽線実体内であれば強気で買いを検討できます。", "出来高が伴っていれば信頼性はさらに高まります。"],
        "desc_lead": "前日の陰線を陽線が完全に包み込む",
        "desc_body": "下落の後の反発で、前日の値動きを消し去る強い買いが出た形です。",
        "detail_desc": "トレンド転換の最も有名なサインの一つ。売りの勢いが完全に買いに食い尽くされたことを示します。",
        "scene": "底値圏での反転初動、上昇の加速局面",
        "howto": "2本目の実体が1本目を完全に覆っているか確認",
    },
    {
        "id": "bear_engulfing",
        "name": "包み足（陰の包み・抱き線）",
        "group": "advanced",
        "category": "陰線",
        "tone": "bearish",
        "svg": "images/candle_patterns/bear_engulfing.svg",
        "action": "売り（前日安値を割り込んだら即撤退）",
        "tips": ["上昇トレンドの終焉を示唆します。陽線を完全に飲み込む陰線が出たら、まずは利益確定を最優先してください。", "翌日に窓を開けて下落が始まる場合は、下げが加速するリスクが高いです。"],
        "desc_lead": "前日の陽線を陰線が完全に包み込む",
        "desc_body": "上昇の後の反落で、前日の上昇分をすべて打ち消す強い売りが出た形です。",
        "detail_desc": "高値圏での「抱き線」は、買い方の力尽きを意味します。ここを起点に急落に転じることが多く、要注意です。",
        "scene": "天井圏での反落開始、急落の予兆",
        "howto": "2本目の実体が1本目を完全に覆っているか確認",
    },
    {
        "id": "harami",
        "name": "はらみ足（陽のはらみ）",
        "group": "advanced",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/candle_patterns/harami.svg",
        "action": "様子見（レンジを上抜けるまで待ち）",
        "tips": ["大きな陰線の後に小さな陽線が現れる「はらみ」は、売りが止まったサインです。翌日、1本目の実体の高値を上抜けてくれば買いのチャンスです。", "焦って買うよりも、放れを確認する順張りが安全です。"],
        "desc_lead": "前日の長い陰線の中に小さな陽線が収まる",
        "desc_body": "激しい売りのあと、一転して小康状態に入った形です。",
        "detail_desc": "売りの勢いが一旦停止したことを示します。ここから反発するか、再度下落するかを見極める重要な「タメ」の局面です。",
        "scene": "下落の最終盤や保ち合いの端",
        "howto": "2本目の実体が1本目の中に納まっているか確認",
    },
    {
        "id": "inyo_harami",
        "name": "陰陽はらみ",
        "group": "advanced",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/candle_patterns/bull_bear_harami.svg",
        "action": "買い（放れを確認してエントリー）",
        "tips": ["底打ちを示唆するパターンです。売りの枯渇と買いの慎重な発生を意味し、翌日に前日の高値を抜ければ反転が確定しやすくなります。", "安値圏であれば強力なサポートラインとして機能します。"],
        "desc_lead": "陰線の実体内に小さな陽線",
        "desc_body": "大きな下落の後に、小さな陽線が包まれた状態です。",
        "detail_desc": "底打ちを示唆するパターンです。売りの枯渇と買いの慎重な発生を意味し、翌日に窓を開けて上昇し始めると反転が確定します。",
        "scene": "下落の極端な安値圏",
        "howto": "一昨日の大陰線と昨日の小陽線の位置関係を確認",
    },
    {
        "id": "kiriage",
        "name": "切り上げ線",
        "group": "advanced",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/candle_patterns/kiriage.svg",
        "action": "買い（安値更新拒否を確認して買い）",
        "tips": ["徐々に安値を切り上げている状態であり、買い手の意欲が高まっています。直近の抵抗線を越えれば、上昇トレンドへと発展する可能性が高いです。", "「押し目」としても機能しやすい形です。"],
        "desc_lead": "安値が順次切り上がる陽線の連続",
        "desc_body": "緩やかに、しかし着実に買い勢力が優勢になりつつある状態。",
        "detail_desc": "上昇トレンドの初期段階や、持ち合いからの上放れ前に見られます。下値の堅さが意識されます。",
        "scene": "安値圏からの脱出、トレンド初期",
        "howto": "直近数本の足の安値が切り上がっているか確認",
    },
    {
        "id": "kirisage",
        "name": "切り下げ線",
        "group": "advanced",
        "category": "陰線",
        "tone": "bearish",
        "svg": "images/candle_patterns/kirisage.svg",
        "action": "売り（高値更新失敗を確認して売り）",
        "tips": ["高値を更新できず、徐々に価格帯が下がっている非常に重い形です。サポートラインを割り込むと、下落に拍車がかかります。", "早めの損切り、または空売りを検討する局面です。"],
        "desc_lead": "高値が順次切り下がる陰線の連続",
        "desc_body": "買い勢力が弱まり、売りがじわじわと強まっている状態。",
        "detail_desc": "下落トレンドの継続や、天井圏からの崩落の予兆です。戻り売りの急所となることが多いです。",
        "scene": "天井圏での失速、下落トレンド中",
        "howto": "直近数本の足の高値が切り下がっているか確認",
    },
    {
        "id": "kabuse",
        "name": "かぶせ線",
        "group": "advanced",
        "category": "陰線",
        "tone": "bearish",
        "svg": "images/candle_patterns/kabuse.svg",
        "action": "売り警戒（高値での窓埋め失敗で売り）",
        "tips": ["上昇にブレーキがかかった強いサインです。特に「かぶせ」の陰線の終値が、前日陽線の中心より下にあるほど反落の確度が高まります。", "翌日に窓を開けて下落すれば、トレンド転換が決定づけられます。"],
        "desc_lead": "前日終値より高く始まり、安値圏で引ける",
        "desc_body": "前日の陽線に対して、窓を開けて高く始まるが、陽線の中心より下まで売られた陰線。",
        "detail_desc": "高値圏での利益確定売りの強さを示します。買い方が高値を維持できず、一気に押し戻された非常に弱い形です。",
        "scene": "上昇トレンドの大詰め、強力な抵抗線付近",
        "howto": "陰線の終値が前日実体の半分以下まで食い込んでいるか確認",
    },
    {
        "id": "sashikomi",
        "name": "差し込み線",
        "group": "advanced",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/candle_patterns/sashikomi.svg",
        "action": "様子見（戻り売り圧力を確認）",
        "tips": ["反発の兆しは見えますが、前日の陰線の中心を越えられない「差し込み」は、まだ下落圧力が根強いことを示しています。", "翌日に前日終値を上回れなければ、再下落のリスクがあるため注意が必要です。"],
        "desc_lead": "前日の陰線の安値付近から始まり、実体の中まで上昇",
        "desc_body": "大きな陰線のあと、窓を開けて低く始まるが、前日の中央部までは届かない程度の反発を見せた形。",
        "detail_desc": "反発が弱く、戻り売りのターゲットになりやすい局面です。「切り返し」になるか「だまし」になるかの瀬戸際です。",
        "scene": "下落トレンド中の一時的な自律反発",
        "howto": "陽線の終値が前日実体の中央を下回っていないか確認",
    },
    {
        "id": "kenuki_zoko",
        "name": "毛抜き底",
        "group": "advanced",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/candle_patterns/kenuki_zoko.svg",
        "action": "買い（二番底確認でエントリー）",
        "tips": ["2本の足の安値がほぼ一致しており、その価格帯が強力な岩盤（サポート）になっていることを示します。安値圏で出た場合、非常に信頼度の高い底打ちサインです。", "下ヒゲが長いほど、反発力はより強固になります。"],
        "desc_lead": "2日続けて安値がほぼ一致する",
        "desc_body": "一度売られたが、翌日も同じ価格でピタリと止まった底堅い形です。",
        "detail_desc": "下値を2回以上同じ価格で叩いても割れなかったことで、売り枯れと買い支えの強さが証明された状態です。",
        "scene": "下落トレンドの最終局面、二番底、三番底",
        "howto": "2本の足の安値（ヒゲも含む）が一致しているか確認",
    },
    {
        "id": "kenuki_tenjo",
        "name": "毛抜き天井",
        "group": "advanced",
        "category": "陰線",
        "tone": "bearish",
        "svg": "images/candle_patterns/kenuki_tenjo.svg",
        "action": "売り（高値不変を確認して利確）",
        "tips": ["2本の足の高値が一致し、上昇が阻まれた形です。高値圏でこの形が出たら、上昇エネルギーが完全に枯渇したと判断し、早期の利確を検討してください。", "ダブルトップの非常に短いスパンでの形成とも言えます。"],
        "desc_lead": "2日続けて高値がほぼ一致する",
        "desc_body": "一度上げたが、翌日も同じ高値でピタリと跳ね返された天井を示す形です。",
        "detail_desc": "高値を2回試して抜けなかったことで、強い上売り圧力が確認された状態です。反落へ転じる可能性が非常に高いです。",
        "scene": "上昇トレンドの天井、重要節目",
        "howto": "2本の足の高値（ヒゲも含む）が一致しているか確認",
    },
    {
        "id": "daki_bull",
        "name": "抱き線（陽）",
        "group": "advanced",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/candle_patterns/daki_bull.svg",
        "action": "買い（トレンド転換を狙う）",
        "tips": ["前日の実体を完全に包み込む大陽線は、相場の主導権が買い方に移ったことを示します。安値圏での出現は、絶好の買い場となります。", "包み足と同意ですが、特に「抱き」と呼ばれる場合は勢いの強さが強調されます。"],
        "desc_lead": "前日の陰線を陽線が完全に包み込む",
        "desc_body": "下落の後に、前日の値動きを消し去る強い買いが出た形です。",
        "detail_desc": "圧倒的な力の逆転。下落局面で出た場合は、トレンド転換の爆発的なエネルギーを示します。",
        "scene": "パニック売り直後のリバウンド局面",
        "howto": "今日の陽線が前日の全てを飲み込んでいるか確認",
    },
    {
        "id": "daki_bear",
        "name": "抱き線（陰）",
        "group": "advanced",
        "category": "陰線",
        "tone": "bearish",
        "svg": "images/candle_patterns/daki_bear.svg",
        "action": "売り（即時撤退を推奨）",
        "tips": ["上昇トレンドを完全に帳消しにする強烈な売りです。高値圏で発生すると、その後数日間にわたる本格的な調整に入るリスクが高いです。", "迷わずポジションを縮小すべき局面です。"],
        "desc_lead": "前日の陽線を陰線が完全に包み込む",
        "desc_body": "上昇の後に、前日の上昇分をすべて打ち消す強い売りが出た形です。",
        "detail_desc": "ここからの大幅下落を示唆します。高値圏で発生すると、その後数日間にわたる調整に入るリスクが高いです。",
        "scene": "上昇加速後のピーク、バブルの終焉",
        "howto": "今日の陰線が前日の全てを飲み込んでいるか確認",
    },
    {
        "id": "kaeshi",
        "name": "返し線",
        "group": "advanced",
        "category": "迷い",
        "tone": "neutral",
        "svg": "images/candle_patterns/kaeshi.svg",
        "action": "様子見（方向性が定まるのを待つ）",
        "tips": ["前日の動きをそのまま打ち消す逆の足が出る「返し」は、売り買いが非常に激しく拮抗している証拠です。現在の価格帯が強い抵抗、または支持になっている可能性があります。", "レンジの中央として機能しやすいため、どちらかに窓を開けて放れるのを待ちましょう。"],
        "desc_lead": "前日の動きをそのまま打ち消す逆の足",
        "desc_body": "陽線のあとに同じくらいの長さの陰線、あるいはその逆が出る形。",
        "detail_desc": "市場の迷いとエネルギーの相殺を示します。トレンドの途中で出現すると、一時的な足踏み状態となります。",
        "scene": "トレンドの中段、材料待ち",
        "howto": "2本の足の実体の長さがほぼ同じで、逆の性質であることを確認",
    },
    {
        "id": "kubitsuri",
        "name": "首吊り線",
        "group": "advanced",
        "category": "陰線",
        "tone": "bearish",
        "svg": "images/candle_patterns/kubitsuri.svg",
        "action": "売り（高値圏での急落に警戒）",
        "tips": ["高値圏で出現する下ヒゲの長い小陰線は、買い支えが限界に来ていることを示します。翌日に安値を更新して始まれば、一気にパニック売りが広がるリスクがあるため、利確を急ぎましょう。", "形は「ハンマー」に似ていますが、出現場所が高値圏である場合は正反対の最悪なサインとなります。"],
        "desc_lead": "高値圏で出る下ヒゲの長い形（小陰線）",
        "desc_body": "安値まで売られた後、買い戻されたが陽転できず、高値圏で引けた形。",
        "detail_desc": "形は反転に見えますが、高値圏で出ると「最後に残っていた買いが使い果たされた」と解釈され、翌日から急落するリスクがある不吉な形。 ",
        "scene": "上昇トレンドの最終盤、クライマックス",
        "howto": "高値圏で下ヒゲが極端に長い陰線を探す",
    },

    # Advanced 3-Candle
    {
        "id": "three_white_soldiers",
        "name": "赤三兵",
        "group": "advanced",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/candle_patterns/three_white_soldiers.svg",
        "action": "買い（強いトレンドに乗る）",
        "tips": ["安値圏で窓を開けずに陽線が3本続くのは、本格的な上昇トレンドの開始を意味します。各陽線の高値が着実に切り上がっていることを確認し、順張りでエントリーしましょう。", "ヒゲが短いほど買い手の意志が強く、信頼性が高まります。"],
        "desc_lead": "陽線が3本連続し、高値を更新し続ける",
        "desc_body": "前日の終値付近から始まり、さらに高く引ける陽線が3日続く形です。",
        "detail_desc": "トレンド転換の最も信頼できるシグナルの一つです。力強い上昇相場の幕開けを示し、長期保有に適したエントリーポイントです。",
        "scene": "長い下落トレンドからの反転初動",
        "howto": "3本の陽線が等間隔、かつ徐々に高値を更新しているか確認",
    },
    {
        "id": "three_black_crows",
        "name": "黒三兵（三羽烏）",
        "group": "advanced",
        "category": "陰線",
        "tone": "bearish",
        "svg": "images/candle_patterns/three_black_crows.svg",
        "action": "売り（下落局面の初期として警戒）",
        "tips": ["上昇トレンドの崩壊を示唆する非常に強い売りサインです。3日連続で安値を切り下げる動きは、買い手の完全な敗北を意味します。", "高値圏で出現した場合は、早急にポジションを外すことを検討してください。"],
        "desc_lead": "陰線が3本連続し、安値を更新し続ける",
        "desc_body": "高値圏から、3日連続で下値を切り下げる陰線が現れる形。",
        "detail_desc": "上昇トレンドの崩壊。非常に強い売り抜けを示唆し、ここから本格的な下落トレンドへの雪崩現象が起きやすくなります。",
        "scene": "高値圏での急落、トレンド終了",
        "howto": "3本の陰線が連続し、上ヒゲが短いことを確認",
    },
    {
        "id": "morning_star",
        "name": "明けの明星",
        "group": "advanced",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/candle_patterns/morning_star.svg",
        "action": "買い（反転確定を確認してエントリー）",
        "tips": ["下落の果てに現れる、反転を予兆する3本の組み合わせです。2本目の「星」が窓を開けて安値で出現し、3本目の陽線が1本目の陰線の中心より上に届けば、強力な底打ちサインです。", "迷わず買いを検討できる非常に信頼度の高いパターンです。"],
        "desc_lead": "長い陰線・十字線・陽線の3点セット",
        "desc_body": "大きな下落のあとに小星が現れ、その後に力強く反発する形。",
        "detail_desc": "夜が明けて太陽が昇るように、相場が底を打って上昇に転じることを示します。三要素が揃うことで非常に高い転換精度を誇ります。",
        "scene": "長期下落トレンドの歴史的な安値圏",
        "howto": "2本目が窓開け（ギャップ）を伴っているか、3本目が強く反発しているか確認",
    },
    {
        "id": "evening_star",
        "name": "宵の明星",
        "group": "advanced",
        "category": "陰線",
        "tone": "bearish",
        "svg": "images/candle_patterns/evening_star.svg",
        "action": "売り（天井を確認して利確）",
        "tips": ["上昇トレンドの終焉を示す不吉なサインです。高値圏で窓を開けて星が出現し、その後大陰線で陽線の安値を割り込むようなら、一刻も早い撤退が求められます。", "「夜の始まり」を意味し、ここから相場は暗転（下落）する可能性が極めて高いです。"],
        "desc_lead": "長い陽線・十字線・陰線の3点セット",
        "desc_body": "大きな上昇のあとに小星が現れ、その後に力強く反落する形。",
        "detail_desc": "相場が天井を打ち、下落への激しい落差が生じるサインです。買いの勢いが急激に萎えてパニック売りに変わる分岐点です。",
        "scene": "バブル的な上昇の最後、主要抵抗線での跳ね返り",
        "howto": "2本目の star が高値で孤立し、3本目の陰線が深く押し込んでいるか確認",
    },
    {
        "id": "sanbagarasu",
        "name": "三羽烏",
        "group": "advanced",
        "category": "陰線",
        "tone": "bearish",
        "svg": "images/candle_patterns/sanbagarasu.svg",
        "action": "売り（暴落の初動を警戒）",
        "tips": ["高値圏で大陰線が3本続くのは、パニック売りや悪材料の織り込み不足を示唆します。各陰線の始値が前日の安値より低く始まる場合は、目も当てられない暴落に発展することがあります。", "勇気を持って一度キャッシュポジションに戻るべき、不吉なサインです。"],
        "desc_lead": "陰線が3本重なり、窓を開けずに急落する",
        "desc_body": "前日終値付近から始まり、さらに安く引ける陰線が3日続く不気味な形です。",
        "detail_desc": "相場の暴落の始まり。強力な売り叩きを意味し、これまでの上昇益をすべて吐き出すような急落の初動によく見られます。",
        "scene": "天井圏からの崩落、重要な節目を割った後の加速",
        "howto": "3本の陰線が窓を開けずに、しかし確実にかぶさりながら下げているか確認",
    },
    {
        "id": "sanku_tatakikomi",
        "name": "三空叩き込み",
        "group": "advanced",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/candle_patterns/sanku_tatakikomi.svg",
        "action": "買い（逆張り・リバウンド狙い）",
        "tips": ["4本の足の間で合計3つの窓を空けて急落する形です。相場がパニック状態にあり、売られすぎの極致に達していることを示します。", "「三空踏み上げ」の逆で、非常に強力なリバウンドが期待できる買い場（底打ち）となります。"],
        "desc_lead": "窓（空）を3つ空けて急落する",
        "desc_body": "連続して窓を空けながら、一方的に売り込まれる極端な形。",
        "detail_desc": "究極の「売られすぎ」サイン。エネルギーが完全に枯渇し、ここからは些細な買い材料で急反発する準備が整った状態です。",
        "scene": "暴落の最終局面、セリングクライマックス",
        "howto": "4本のローソク足の間に、3つの窓（隙間）が明確にあるか確認",
    },
    {
        "id": "rising_three_methods",
        "name": "上げ三法",
        "group": "advanced",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/candle_patterns/rising_three_methods.svg",
        "action": "買い（エネルギー蓄積後の上放れで買い）",
        "tips": ["大陽線の後に小陰線が3本続くのは、上昇力を蓄えるための健全な休憩（押し目）です。5本目の足が大陽線となり、1本目の高値を抜ければ、上昇トレンドはさらに加速します。", "休んでいる間に売られすぎないことが、強いトレンドの条件です。"],
        "desc_lead": "大陽線の後の小陰線3本を経て再上昇",
        "desc_body": "大陽線のあとに小さな陰線が3本続き、再度大陽線で上抜ける形。",
        "detail_desc": "上昇トレンド継続の最強パターン。調整が1本目の大陽線実体内で終わる限り、上昇エネルギーは温存されています。",
        "scene": "強い上昇トレンドの中休み",
        "howto": "中央の小足が大陽線の実体内に収まっているか確認",
    },
    {
        "id": "falling_three_methods",
        "name": "下げ三法",
        "group": "advanced",
        "category": "陰線",
        "tone": "bearish",
        "svg": "images/candle_patterns/falling_three_methods.svg",
        "action": "売り（リバウンド失敗を確認して売り）",
        "tips": ["大陰線の後の小陽線3本は、ただの自律反発に過ぎません。5本目の大陰線が1本目の安値を更新すれば、下落トレンドの継続は決定的となります。", "中途半端なリバウンドで買わず、安値更新を待って売りで付いていきましょう。"],
        "desc_lead": "大陰線の後の小陽線3本を経て再下落",
        "desc_body": "大陰線のあとに小さな陽線が3本続き、再度大陰線で下抜ける形。",
        "detail_desc": "下落トレンド継続の典型例。戻り売り圧力が極めて強く、買い方が完全に力尽きたことを示します。",
        "scene": "下落トレンドの中休み、戻り売りの急所",
        "howto": "中央の小足が大陰線の実体内に収まっているか確認",
    },
    {
        "id": "sutego",
        "name": "捨て子線",
        "group": "advanced",
        "category": "迷い",
        "tone": "neutral",
        "svg": "images/candle_patterns/sutego.svg",
        "action": "即時エントリー/撤退（強力な転換サイン）",
        "tips": ["前後の足から窓を空けて完全に孤立した十字線は、トレンドが極限まで達して完全に力尽きたことを示します。安値圏なら「買い」、高値圏なら「即売り」の極めて強力なサインです。", "滅多に出現しませんが、信頼性は全パターンの中でもトップクラスです。"],
        "desc_lead": "上下に窓（空）を空けて孤立する十字線",
        "desc_body": "前後の足と全く連結していない、ポツンと離れた十字。",
        "detail_desc": "トレンドの「断絶」を意味します。ここを境に相場の流れが一変することが多く、非常に重視すべきシグナルです。",
        "scene": "相場のクライマックス、トレンド転換の大本命",
        "howto": "真ん中の十字線のヒゲすら、前後の足と重ならないことを確認",
    },
    {
        "id": "sanpei_hasami",
        "name": "三兵挟み",
        "group": "advanced",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/candle_patterns/sanpei_hasami.svg",
        "action": "買い（押し目としてエントリー）",
        "tips": ["上昇の勢いの中で一時的に利確売りが出ましたが、すぐさま買い戻された「押し目」の形です。真ん中の陰線を次の陽線がすぐに上書きすれば、上昇トレンド継続は安泰です。", "深い調整（押し）にならないため、非常に強い地合いであることを示しています。"],
        "desc_lead": "上昇トレンド中に1本だけ陰線を挟む",
        "desc_body": "陽・陰・陽の並びだが、真ん中の陰腺が小さく、上昇の流れを壊さない。",
        "detail_desc": "利益確定売りを十分にこなしながら上昇している健康的な形。急騰しすぎず、息の長い上昇トレンドになりやすいです。",
        "scene": "緩やかな上昇トレンドの途中",
        "howto": "陰線を次の陽線ですぐに上書き（包み込む）するか見る",
    },
    {
        "id": "gyaku_sanzon",
        "name": "逆三尊型",
        "group": "advanced",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/candle_patterns/gyaku_sanzon.svg",
        "action": "買い（ネックライン上放れでエントリー）",
        "tips": ["底値圏で3つの谷を作る「逆三尊」は、これ以上下がらないという強固な意志の表れです。左右の谷よりも中央の谷が深いことが特徴で、ネックラインを突破すれば大相場へ発展する可能性が高いです。", "多くの投資家が注目する「鉄板」の底入れサインです。"],
        "desc_lead": "3つの谷を作る強力な底打ち形状",
        "desc_body": "左肩、頭（中央最安値）、右肩を形成して、ネックラインを抜ける。",
        "detail_desc": "底入れの最も有名な形。ここでは簡略化して見せますが、大規模な転換点として、大口投資家も重視する最重要ポイントです。",
        "scene": "大底圏での大がかりな地固め",
        "howto": "中央が最も低く、左右の谷が揃っているか確認",
    },
    {
        "id": "harami_sanbon",
        "name": "はらみ三本",
        "group": "advanced",
        "category": "迷い",
        "tone": "neutral",
        "svg": "images/candle_patterns/harami_sanbon.svg",
        "action": "様子見（レンジを上抜けるまで待ち）",
        "tips": ["「はらみ足」の後にレンジを抜けきれない状態です。方向感が完全に定まっていないため、初日の大足の高値または安値をどちらに放れるかを確認するまで静観が賢明です。", "エネルギーは十分蓄積されており、放れた時の動きは大きくなります。"],
        "desc_lead": "はらみの後に、前々日の実体を抜けられない状態",
        "desc_body": "二日間の「はらみ」状態から、三日目の足もまだレンジ内に留まっている形。",
        "detail_desc": "はらみ足によるエネルギー蓄積が続いています。三日目の足がトレンドを決定づけることが多く、抜けた方向に付いていく準備をしましょう。",
        "scene": "保ち合いの最終局面",
        "howto": "三日目の足が、初日の大足の高値を抜けるか安値を割るかを確認",
    },
    {
        "id": "island_reversal",
        "name": "アイランドリバーサル",
        "group": "advanced",
        "category": "迷い",
        "tone": "neutral",
        "svg": "images/candle_patterns/island_reversal.svg",
        "action": "売り（高値圏）/ 買い（安値圏）",
        "tips": ["窓と窓に挟まれて価格帯が孤立する形は、市場心理の劇的な変化（パニックや熱狂の終了）を意味します。孤島のようになった価格帯が強力な壁となり、以後その価格帯に戻るのは困難になります。", "放れた方向に強いトレンドが発生するため、逆らわずに付いていきましょう。"],
        "desc_lead": "窓と窓に挟まれた取り残された価格帯",
        "desc_body": "窓を開けて跳んだあと、さらに逆方向に窓を開けて戻る、孤島のような形。",
        "detail_desc": "市場参加者の「総入れ替え」が起きた印。窓の価格帯には商いがないため、強力な支持や抵抗として機能し続けます。",
        "scene": "急激な流れの変化、ニュースによる反落反騰",
        "howto": "「窓」によって他のロウソク足と切り離された塊を探す",
    },
    {
        "id": "sanzan",
        "name": "三山（三尊型）",
        "group": "advanced",
        "category": "陰線",
        "tone": "bearish",
        "svg": "images/candle_patterns/sanzan.svg",
        "action": "売り（ネックライン割れで撤退）",
        "tips": ["3つの山（高値）を作る「三山」は、上昇エネルギーが三度試して尽きたことを示す最も有名な天井サインです。ネックラインを割り込むと、長期的な下落トレンドへの入り口となります。", "「酒田五法」における代表的な天井サインであり、警戒が必要です。"],
        "desc_lead": "3つの山を形成する強力な天井形状",
        "desc_body": "高値で3回跳ね返され、ネックラインを割り込む形。",
        "detail_desc": "天井圏形成の最も有名な形の一つ。逆三尊の逆で、非常に強い売り圧力を示唆します。長期的な下落局面への入り口です。",
        "scene": "上昇トレンドの大天井",
        "howto": "3本の山が形成され、その後安値を割り込むか見る",
    },

    # Reference Patterns (Windows/Gaps)
    {
        "id": "gap_up",
        "name": "窓開け（ギャップアップ）",
        "group": "advanced",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/candle_patterns/gap_up.svg",
        "action": "買い検討（強い材料を伴う上放れ）",
        "tips": ["前日の価格帯を飛び越えて高く始まるのは、買い意欲が極めて強い証拠です。窓が埋まらない限り、上昇トレンドは加速しやすくなります。", "ただし、あまりに大きな窓は、寄り付き後の利益確定売りに押されるリスクがあるため注意しましょう。"],
        "desc_lead": "前日終値よりも大幅に高く寄り付く",
        "desc_body": "前日の価格帯と全く重ならない高い位置から取引が始まること。",
        "detail_desc": "需要が供給を圧倒的に上回っている証拠。強い材料（決算等）があった際に出やすく、トレンド加速の強力なエネルギーです。",
        "scene": "好決算発表翌日、新サービス発表後",
        "howto": "前日の高値と今日の安値に「空白」があるか確認",
    },
    {
        "id": "gap_down",
        "name": "窓開け（ギャップダウン）",
        "group": "advanced",
        "category": "陰線",
        "tone": "bearish",
        "svg": "images/candle_patterns/gap_down.svg",
        "action": "売り警戒（失望売りによる下放れ）",
        "tips": ["前日の価格帯を下抜けて低く始まるのは、失望売りが集中している極めて弱い状態です。この窓が埋まらずに下げ続ける場合、長期的な下落トレンドに繋がる恐れがあります。", "安易な「リバウンド狙い」は避け、パニックが収まるのを待ちましょう。"],
        "desc_lead": "前日終値よりも大幅に低く寄り付く",
        "desc_body": "前日の価格帯と連結せず、低く引き離されて取引が始まること。",
        "detail_desc": "失望売りの集中。心理的な節目を窓で割ると、その後長期的な低迷期に入る恐れも。",
        "scene": "下方修正、不祥事、地政学リスクの顕在化",
        "howto": "前日の安値と今日の高値に「空白」があるか確認",
    },
    {
        "id": "gap_fill",
        "name": "窓埋め",
        "group": "advanced",
        "category": "迷い",
        "tone": "neutral",
        "svg": "images/candle_patterns/gap_fill.svg",
        "action": "様子見（埋めた後の反転を待つ）",
        "tips": ["窓を空けて上昇した後の調整で、その空白（窓）を埋める動きを指します。窓は埋まると、そこが強力な支持（あるいは抵抗）として機能することが多いです。", "窓を埋めた直後の反転は、絶好のトレンド再開ポイントとなることがあります。"],
        "desc_lead": "開いた窓を埋めるように価格が戻る",
        "desc_body": "窓が開いたあとに、その空白となっていた価格帯を埋める動き。",
        "detail_desc": "「窓は必ず埋まる」という相場格言がありますが、現実は窓埋め後に再びトレンド方向に戻ることが多く、絶好の押し目・戻り売りポイントです。",
        "scene": "急騰・急落後の自律調整局面",
        "howto": "窓の部分まで株価がタッチしたかを確認",
    },
    {
        "id": "madokan_sanpou",
        "name": "窓開け三法",
        "group": "advanced",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/candle_patterns/madokan_sanpou.svg",
        "action": "買い（強いトレンドに乗る）",
        "tips": ["窓を開けて上昇したあと、窓を埋めることなくエネルギーを蓄積し、再び上抜ける極めて強い形です。窓を開けるエネルギーが一時的なものではなく、本物であることを示しています。", "最強の上昇トレンド継続サインの一つです。"],
        "desc_lead": "窓開けのあと、中休みを経て再加速",
        "desc_body": "窓を開けた大陽線のあと、窓を埋めずに小休止し、再度上放れる形。",
        "detail_desc": "酒田五法の応用。窓を開けるほどのエネルギーが本物であることを証明する形です。長期の上昇トレンドにつながりやすいです。",
        "scene": "大相場の初動から中盤",
        "howto": "窓が埋まらなかったことを確認し、再度の高値更新を狙う",
    },
    {
        "id": "sakata_gohou",
        "name": "酒田五法",
        "group": "advanced",
        "category": "迷い",
        "tone": "neutral",
        "svg": "images/candle_patterns/sakata_gohou.svg",
        "action": "相場観の確認（基本原則の復習）",
        "tips": ["三山・三川・三空・三兵・三法の五つの法則を指します。市場参加者の熱狂と絶望を読み解くための「哲学」とも呼べる基本原則です。", "江戸時代の米相場から続くこの英知は、現代の株式相場でも極めて有効です。"],
        "desc_lead": "ローソク足分析の原点、五つの基本原則",
        "desc_body": "三山・三川・三空・三兵・三法の総称。日本が世界に誇る相場の真髄です。",
        "detail_desc": "単なる図形ではなく、市場参加者の心理状態を把握するための方法論です。すべてのロウソク足分析の基礎となります。",
        "scene": "あらゆる局面で参照される基本概念",
        "howto": "それぞれの代表的な形を複合的に判断する",
    },
    {
        "id": "range_break",
        "name": "レンジブレイク",
        "group": "advanced",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/candle_patterns/range_break.svg",
        "action": "買い検討（ブレイク直後の勢いに乗る）",
        "tips": ["長期間続いた均衡（レンジ）を上抜けるのは、新しいトレンドが発生した強力なサインです。溜め込んだエネルギーが一気に解放されるため、大きな上昇が期待できます。", "ブレイクしたラインが、今度は強力な支持線（サポート）として機能するようになります。"],
        "desc_lead": "長期間の持ち合いを突き抜ける一本",
        "desc_body": "一定の価格帯（レンジ）を、大陽線や窓で力強く上抜けること。",
        "detail_desc": "売り手と買い手の均衡が崩れたシグナル。レンジの期間が長いほど、その後の上昇の幅は大きくなります。順張りのチャンス。",
        "scene": "長いボックス圏を抜けて新高値を取る時",
        "howto": "これまでの抵抗線を突き抜けたことを確認",
    },
    {
        "id": "volume_window",
        "name": "出来高伴う窓形成",
        "group": "advanced",
        "category": "陽線",
        "tone": "bullish",
        "svg": "images/candle_patterns/volume_window.svg",
        "action": "買い（強い需要を確認して買い）",
        "tips": ["出来高を伴った窓開けは、機関投資家などの大口の資金が流入している証拠です。単なる窓開けよりも信頼性が格段に高く、その後のトレンドが長続きする傾向があります。", "窓開け当日の出来高が直近平均の数倍あれば、非常に強力なサインです。"],
        "desc_lead": "窓開けと同時に出来高が急増",
        "desc_body": "窓が開くと同時に、普段の数倍の売買が行われた状態。",
        "detail_desc": "単なる窓よりもはるかに信頼度が高いです。機関投資家や大口の意志が反映されており、この窓が埋まるには相当の悪材料が必要になります。",
        "scene": "サプライズ決算へのポジティブ反応",
        "howto": "窓の大きさと共に、下の出来高バーの高さに注目",
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


def get_stock_list(db: Session) -> List[Dict[str, Any]]:
    """
    ウォッチリスト銘柄の最新情報を取得してリストで返す。
    リアルタイムデータ取得を行い、失敗時はキャッシュまたはNoneを返す。
    """
    stocks: List[Dict[str, Any]] = []
    for code in get_watchlist_codes(db):
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
        "trend_label": trend_label,
        "trend_desc": trend_desc,
        "chart_payload": {
            "points": points,
            "support_levels": support_levels,
            "candle_patterns": CANDLE_PATTERN_CARDS
        },
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
    """配当タブ用の全データを構築する。"""
    symbol = format_symbol_for_yfinance(code)

    # --- データ取得 ---
    details = fetch_dividend_details(symbol)
    records = details.get("records", [])
    current_price = details.get("current_price")
    trailing_eps = details.get("trailing_eps")

    # ------------------------------------------------------------------
    # 1) 権利日情報
    # ------------------------------------------------------------------
    ex_div = details.get("ex_dividend_date") or "—"
    rec_date = details.get("record_date") or "—"

    # 権利付き最終日 = 権利落ち日の1営業日前（簡易: 1日前）
    last_trading_day = "—"
    if ex_div != "—":
        try:
            from datetime import timedelta
            ex_dt = datetime.strptime(ex_div, "%Y/%m/%d")
            ltd = ex_dt - timedelta(days=1)
            last_trading_day = ltd.strftime("%Y/%m/%d")
        except Exception:
            pass

    rights_dates = {
        "last_trading_day": last_trading_day,
        "ex_dividend_date": ex_div,
        "record_date": rec_date,
    }

    # ------------------------------------------------------------------
    # 2) 年度別集計（通常配当 / 特別配当）
    # ------------------------------------------------------------------
    yearly: Dict[int, Dict[str, float]] = {}  # {year: {"ordinary": x, "special": y}}
    for r in records:
        dt = r["date"]
        year = dt.year if hasattr(dt, "year") else None
        if year is None:
            continue
        if year not in yearly:
            yearly[year] = {"ordinary": 0.0, "special": 0.0}
        dtype = r.get("type", "通常")
        if dtype == "特別":
            yearly[year]["special"] += r["amount"]
        else:
            yearly[year]["ordinary"] += r["amount"]

    sorted_years = sorted(yearly.keys())

    # 直近年度 / 前年度
    latest_year = sorted_years[-1] if sorted_years else None
    prev_year = sorted_years[-2] if len(sorted_years) >= 2 else None

    annual_ordinary = yearly[latest_year]["ordinary"] if latest_year else None
    annual_special = yearly[latest_year]["special"] if latest_year else None
    annual_total = (annual_ordinary or 0) + (annual_special or 0) if latest_year else None
    has_special = (annual_special or 0) > 0

    prev_ordinary = yearly[prev_year]["ordinary"] if prev_year else None

    # ------------------------------------------------------------------
    # 3) 増配/減配判定（通常配当ベース）
    # ------------------------------------------------------------------
    growth_status = "判定不可"
    growth_pct_val = None
    if annual_ordinary is not None and prev_ordinary is not None and prev_ordinary > 0:
        diff = annual_ordinary - prev_ordinary
        growth_pct_val = (diff / prev_ordinary) * 100
        if diff > 0:
            growth_status = "増配"
        elif diff < 0:
            growth_status = "減配"
        else:
            growth_status = "据置"

    # ------------------------------------------------------------------
    # 4) KPI計算
    # ------------------------------------------------------------------
    # 配当利回り
    yield_pct = "—"
    if annual_total is not None and current_price and current_price > 0:
        y = annual_total / current_price * 100
        yield_pct = f"{y:.1f}%"

    # 増配/減配率
    growth_pct_str = "—"
    if growth_pct_val is not None:
        sign = "+" if growth_pct_val > 0 else ""
        growth_pct_str = f"{sign}{growth_pct_val:.1f}%"

    # 配当性向
    payout_ratio_str = "—"
    if annual_total is not None and trailing_eps and trailing_eps > 0:
        pr = annual_total / trailing_eps * 100
        payout_ratio_str = f"{pr:.1f}%"

    # 連続増配年数（通常配当ベース）
    continuous_years = 0
    if len(sorted_years) >= 2:
        for i in range(len(sorted_years) - 1, 0, -1):
            cur_y = sorted_years[i]
            prv_y = sorted_years[i - 1]
            if yearly[cur_y]["ordinary"] > yearly[prv_y]["ordinary"]:
                continuous_years += 1
            else:
                break

    kpi = {
        "annual_total": f"¥{annual_total:,.1f}" if annual_total is not None else "—",
        "annual_ordinary": f"¥{annual_ordinary:,.1f}" if annual_ordinary is not None else "—",
        "annual_special": f"¥{annual_special:,.1f}" if annual_special is not None else "—",
        "has_special": has_special,
        "growth_status": growth_status,
        "yield_pct": yield_pct,
        "growth_pct": growth_pct_str,
        "payout_ratio_pct": payout_ratio_str,
        "continuous_years": continuous_years if sorted_years else "—",
    }

    # ------------------------------------------------------------------
    # 5) SVGグラフ用データ（年間配当推移）
    # ------------------------------------------------------------------
    chart = {
        "has_data": False,
        "svg_points_ordinary": "",
        "svg_points_special": "",
        "y_labels": [],
        "x_labels": [],
        "viewbox": "0 0 600 260",
        "width": 600,
        "height": 260,
    }
    if len(sorted_years) >= 2:
        chart["has_data"] = True
        all_values = []
        for y in sorted_years:
            all_values.append(yearly[y]["ordinary"])
            if yearly[y]["special"] > 0:
                all_values.append(yearly[y]["ordinary"] + yearly[y]["special"])

        max_val = max(all_values) if all_values else 1
        min_val = 0  # Y軸は0始まり
        val_range = max_val - min_val if max_val > min_val else 1

        # グラフ描画エリア（パディング込み）
        pad_left = 60
        pad_right = 20
        pad_top = 20
        pad_bottom = 30
        draw_w = chart["width"] - pad_left - pad_right
        draw_h = chart["height"] - pad_top - pad_bottom

        n = len(sorted_years)
        x_step = draw_w / max(n - 1, 1)

        pts_ordinary = []
        pts_special = []

        for i, y in enumerate(sorted_years):
            x = pad_left + i * x_step
            # 通常配当
            ord_val = yearly[y]["ordinary"]
            y_ord = pad_top + draw_h - (ord_val - min_val) / val_range * draw_h
            pts_ordinary.append(f"{x:.1f},{y_ord:.1f}")
            # 特別配当（通常＋特別の合計として描画）
            if yearly[y]["special"] > 0:
                total_val = ord_val + yearly[y]["special"]
                y_sp = pad_top + draw_h - (total_val - min_val) / val_range * draw_h
                pts_special.append(f"{x:.1f},{y_sp:.1f}")

        chart["svg_points_ordinary"] = " ".join(pts_ordinary)
        chart["svg_points_special"] = " ".join(pts_special)
        chart["x_labels"] = [{"x": pad_left + i * x_step, "label": str(y)} for i, y in enumerate(sorted_years)]

        # Y軸ラベル（5段階）
        y_step_val = val_range / 4
        for j in range(5):
            val = min_val + j * y_step_val
            y_pos = pad_top + draw_h - j / 4 * draw_h
            chart["y_labels"].append({"y": y_pos, "label": f"¥{val:,.0f}"})

        chart["pad_left"] = pad_left
        chart["pad_top"] = pad_top
        chart["draw_w"] = draw_w
        chart["draw_h"] = draw_h

    # ------------------------------------------------------------------
    # 6) 減配履歴（直近5年・通常配当ベース）
    # ------------------------------------------------------------------
    reduction_history = []
    if len(sorted_years) >= 2:
        recent_years = sorted_years[-6:]  # 最大6年分で5年間の比較
        for i in range(1, len(recent_years)):
            cur_y = recent_years[i]
            prv_y = recent_years[i - 1]
            cur_ord = yearly[cur_y]["ordinary"]
            prv_ord = yearly[prv_y]["ordinary"]
            if prv_ord > 0 and cur_ord < prv_ord:
                pct = (cur_ord - prv_ord) / prv_ord * 100
                reduction_history.append({
                    "year": cur_y,
                    "from_val": f"¥{prv_ord:,.1f}",
                    "to_val": f"¥{cur_ord:,.1f}",
                    "pct": f"{pct:.1f}%",
                })

    # ------------------------------------------------------------------
    # 7) 配当イベント一覧（直近10件）
    # ------------------------------------------------------------------
    dividend_events = []
    for r in records[-10:]:
        dt = r["date"]
        if hasattr(dt, "strftime"):
            date_str = dt.strftime("%Y/%m/%d")
        else:
            date_str = str(dt)
        dividend_events.append({
            "date": date_str,
            "record_date": r.get("record_date") or "—",
            "amount": f"¥{r['amount']:,.1f}",
            "type": r.get("type", "不明"),
        })
    # 最新順に表示
    dividend_events.reverse()

    # ------------------------------------------------------------------
    # 8) XBRLデータ統合（最新の現地保存ファイルがあれば）
    # ------------------------------------------------------------------
    xbrl_info = None
    try:
        # Avoid circular import at top level if necessary, or just import here
        from services.edinet_document_store import EdinetDocumentStore
        store = EdinetDocumentStore()
        
        # Try to find latest XBRL for this code
        xbrl_data = store.find_latest_local_xbrl(code)
        if xbrl_data:
            xbrl_info = {
                "doc_id": xbrl_data.get("doc_id"),
                "period_end": xbrl_data.get("period_end"),
                "dividend_total": xbrl_data.get("dividend_total"),
                "dividend_per_share": xbrl_data.get("dividend_per_share"),
                "filer_name": xbrl_data.get("filer_name"),
            }
            # Format numbers
            if xbrl_info["dividend_total"] is not None:
                try:
                    val = float(xbrl_info["dividend_total"])
                    xbrl_info["dividend_total_fmt"] = f"¥{val:,.0f}"
                except:
                    pass
    except Exception as e:
        logger.error(f"XBRL integration failed for {code}: {e}")

    return {
        "rights_dates": rights_dates,
        "kpi": kpi,
        "chart": chart,
        "reduction_history": reduction_history,
        "dividend_events": dividend_events,
        "xbrl_info": xbrl_info,
    }


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
    
    # Calculate group counts dynamically to ensure consistency
    dynamic_group_counts = {g: 0 for g in group_labels}
    for item in CANDLE_PATTERN_CARDS:
        grp = item.get("group", "basic")
        if grp in dynamic_group_counts:
            dynamic_group_counts[grp] += 1

    return {
        "patterns": CANDLE_PATTERN_CARDS,
        "categories": categories,
        "group_by_category": group_by_category,
        "group_labels": group_labels,
        "group_counts": dynamic_group_counts,
        "category_counts": category_counts,
    }


def get_glossary_terms() -> List[Dict[str, str]]:
    return GLOSSARY_TERMS


def get_timestamp_label() -> str:
    now = datetime.now()
    return now.strftime("(%Y/%m/%d %H:%M 時点)")
