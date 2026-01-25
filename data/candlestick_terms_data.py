"""
ローソク足パターン用データモジュール
ローソク足の基本形や2本・3本パターンをまとめる
"""

CANDLESTICK_TERMS = {
    "ローソク足の基本形": {
        "陽線": {
            "japanese": "陽線",
            "english": "Bullish Candle",
            "meaning": "終値が始値より高く引けたローソク足。買い優勢を示す。",
            "usage": "上昇トレンドの継続や反転局面での強気シグナルとして注視される。実体が大きいほど勢いが強い。"
        },
        "陰線": {
            "japanese": "陰線",
            "english": "Bearish Candle",
            "meaning": "終値が始値より安く引けたローソク足。売り優勢を示す。",
            "usage": "下降トレンドの継続や反転局面での弱気シグナルとして用いられる。実体が大きいほど売り圧力が強い。"
        },
        "十字線": {
            "japanese": "十字線",
            "english": "Doji",
            "meaning": "始値と終値がほぼ同じで実体が極めて小さいローソク足。迷いを示す。",
            "usage": "トレンド転換の初期サインとして出現することが多い。高値圏では反落、安値圏では反発の兆候として確認される。"
        },
        "カラカサ": {
            "japanese": "カラカサ",
            "english": "Hammer",
            "meaning": "下ヒゲが長く実体が小さいローソク足。底打ちの目安になりやすい。",
            "usage": "下降トレンド終盤での出現が買い転換シグナルとなることが多い。陽線のカラカサはより強気に評価される。"
        },
        "トンカチ": {
            "japanese": "トンカチ",
            "english": "Hanging Man",
            "meaning": "上ヒゲが長く実体が小さいローソク足。天井圏の警戒シグナルとなりやすい。",
            "usage": "上昇トレンド高値圏での出現が売り転換サインとなることが多い。陰線のトンカチはより弱気に評価される。"
        },
        "マルボウズ": {
            "japanese": "マルボウズ",
            "english": "Marubozu",
            "meaning": "ヒゲがほとんどなく実体のみで構成されるローソク足。強い勢いを示す。",
            "usage": "陽線のマルボウズは強い買い圧力、陰線のマルボウズは強い売り圧力を示し、トレンド継続局面でよく使われる。"
        },
        "大陽線": {
            "japanese": "大陽線",
            "english": "Long Bullish Candle",
            "meaning": "実体が大きい陽線。強い買いの流れを示す。",
            "usage": "上昇トレンド継続や底値圏での反転シグナルとして利用される。出来高増加を伴うと信頼性が高まる。"
        },
        "大陰線": {
            "japanese": "大陰線",
            "english": "Long Bearish Candle",
            "meaning": "実体が大きい陰線。強い売りの流れを示す。",
            "usage": "下降トレンド継続や高値圏での反転シグナルとして利用される。出来高増加を伴うと信頼性が高まる。"
        }
    },
    "パターン（2本）": {
        "包み足": {
            "japanese": "包み足",
            "english": "Engulfing Pattern",
            "meaning": "2本目の実体が1本目を完全に包み込むパターン。強い反転シグナル。",
            "usage": "陽の包み足は底値圏での強気反転、陰の包み足は高値圏での弱気反転として用いられる。"
        },
        "はらみ足": {
            "japanese": "はらみ足",
            "english": "Harami Pattern",
            "meaning": "2本目の実体が1本目の実体内に収まるパターン。勢いの減速を示す。",
            "usage": "上昇トレンド高値圏では弱気、下降トレンド安値圏では強気の転換サインとなることが多い。"
        },
        "切り込み線": {
            "japanese": "切り込み線",
            "english": "Piercing Pattern",
            "meaning": "陰線の後に陽線が出現し、前日の実体の半分以上を切り返すパターン。強気反転シグナル。",
            "usage": "底値圏での反転確認に使われ、出来高増加を伴うと信頼性が高い。"
        }
    },
    "パターン（3本）": {
        "明けの明星": {
            "japanese": "明けの明星",
            "english": "Morning Star",
            "meaning": "大陰線→小さな実体→大陽線の3本で構成される強気反転パターン。",
            "usage": "下降トレンド終盤での出現が底打ちサインとなる。3本目が1本目の実体を大きく切り返すほど強い。"
        },
        "宵の明星": {
            "japanese": "宵の明星",
            "english": "Evening Star",
            "meaning": "大陽線→小さな実体→大陰線の3本で構成される弱気反転パターン。",
            "usage": "上昇トレンド高値圏での出現が天井サインとなる。3本目が1本目の実体を深く包むほど強い。"
        },
        "赤三兵": {
            "japanese": "赤三兵",
            "english": "Three White Soldiers",
            "meaning": "連続した3本の陽線が高値を更新し続けるパターン。強い上昇トレンドを示す。",
            "usage": "底値圏からの反転確認として使われる。出来高増加を伴うと継続性の期待が高まる。"
        }
    }
}


def get_candlestick_term_by_category(category: str) -> dict:
    """
    カテゴリ名からローソク足用語データを取得
    """
    return CANDLESTICK_TERMS.get(category, {})


def get_all_candlestick_categories() -> list:
    """
    すべてのローソク足カテゴリ名を取得
    """
    return list(CANDLESTICK_TERMS.keys())


def search_candlestick_terms(keyword: str) -> dict:
    """
    キーワードでローソク足用語を検索する
    """
    results = {}
    keyword_lower = keyword.lower()

    for category, terms in CANDLESTICK_TERMS.items():
        matched_terms = {}
        for term_name, term_data in terms.items():
            search_text = (
                term_data.get("japanese", "")
                + term_data.get("english", "")
                + term_data.get("meaning", "")
                + term_data.get("usage", "")
            ).lower()
            if keyword_lower in search_text:
                matched_terms[term_name] = term_data

        if matched_terms:
            results[category] = matched_terms

    return results


def get_candlestick_term_info(category: str, term_name: str) -> dict:
    """
    特定のローソク足用語の詳細情報を取得
    """
    category_terms = CANDLESTICK_TERMS.get(category, {})
    return category_terms.get(term_name, {})

