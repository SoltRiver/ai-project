"""
用語辞典データモジュール
一般的な投資用語を定義する
"""

TERMS_DATA = {
    "ファンダメンタル指標": {
        "PER": {
            "japanese": "PER",
            "english": "Price Earnings Ratio",
            "meaning": "株価を1株当たり利益（EPS）で割った指標。株価が利益に対して割高か割安かを測る。",
            "usage": "業種平均や過去水準と比較し、割安・割高の目安として使う。単独ではなく成長率や業績見通しと合わせて判断する。"
        },
        "PBR": {
            "japanese": "PBR",
            "english": "Price Book Ratio",
            "meaning": "株価を1株当たり純資産（BPS）で割った指標。企業価値が純資産に対して割安かを示す。",
            "usage": "1倍割れは解散価値以下の可能性を示すことがあるが、収益性や資産の質も合わせて確認する。"
        },
        "配当利回り": {
            "japanese": "配当利回り",
            "english": "Dividend Yield",
            "meaning": "1株当たり配当金を株価で割った指標。投資金額に対する配当収入の割合を示す。",
            "usage": "高配当銘柄の選別に用いられるが、減配リスクや配当性向も合わせてチェックする。"
        },
        "自己資本比率": {
            "japanese": "自己資本比率",
            "english": "Equity Ratio",
            "meaning": "総資産に対する自己資本の割合。財務の健全性を示す。",
            "usage": "一般に40%超で安定的とされるが、業種特性を考慮して比較する。"
        }
    },
    "市場分析の基本": {
        "トレンド": {
            "japanese": "トレンド",
            "english": "Trend",
            "meaning": "価格が上昇・下降・横ばいのどの方向に動いているかを示す。",
            "usage": "上昇トレンドでは押し目買い、下降トレンドでは戻り売りなど、方向性に沿った売買判断の基礎となる。"
        },
        "サポートライン": {
            "japanese": "サポートライン",
            "english": "Support Line",
            "meaning": "価格が下落時に下げ止まりやすい水準。需要が強まりやすい価格帯。",
            "usage": "サポート付近での反発狙いや、割り込み時の損切り基準として利用される。"
        },
        "レジスタンスライン": {
            "japanese": "レジスタンスライン",
            "english": "Resistance Line",
            "meaning": "価格が上昇時に上げ止まりやすい水準。供給が増えやすい価格帯。",
            "usage": "レジスタンス突破は上昇加速のサインとなる一方、跳ね返された場合は利確や反落に注意する。"
        },
        "出来高": {
            "japanese": "出来高",
            "english": "Volume",
            "meaning": "一定期間に成立した取引株数。相場の注目度や流動性を示す。",
            "usage": "価格変動と出来高の関係からトレンドの強さや転換の兆しを読み取る。ブレイク時の増加は信頼性を高める。"
        }
    },
    "テクニカル指標": {
        "移動平均線": {
            "japanese": "移動平均線",
            "english": "Moving Average",
            "meaning": "一定期間の終値平均を線で結んだもの。価格の方向性を滑らかに示す。",
            "usage": "株価が移動平均線の上にあれば上昇トレンド、下にあれば下降トレンドの目安。短期と長期のクロスで売買サインを確認する。"
        },
        "RSI": {
            "japanese": "RSI",
            "english": "Relative Strength Index",
            "meaning": "買われ過ぎ・売られ過ぎを0〜100で示すオシレーター。",
            "usage": "一般に70超で買われ過ぎ、30未満で売られ過ぎとされるが、強いトレンド中は高止まり・低止まりに注意する。"
        },
        "MACD": {
            "japanese": "MACD",
            "english": "Moving Average Convergence Divergence",
            "meaning": "2本の移動平均線の差を使ったトレンドフォロー指標。",
            "usage": "MACDラインがシグナルラインを上抜ければ買い、下抜ければ売りの目安。ヒストグラムの拡大・縮小で勢いを測る。"
        },
        "トレンドライン": {
            "japanese": "トレンドライン",
            "english": "Trend Line",
            "meaning": "高値・安値を結んで方向性を視覚化する補助線。",
            "usage": "上昇トレンドライン割れは弱気サイン、下降トレンドライン突破は強気サインとして活用する。角度や本数で信頼度を確認する。"
        }
    }
}


def get_term_by_category(category: str) -> dict:
    """
    カテゴリ名から用語データを取得
    """
    return TERMS_DATA.get(category, {})


def get_all_categories() -> list:
    """
    すべてのカテゴリ名を取得
    """
    return list(TERMS_DATA.keys())


def search_terms(keyword: str) -> dict:
    """
    キーワードで用語を検索
    """
    results = {}
    keyword_lower = keyword.lower()

    for category, terms in TERMS_DATA.items():
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


def get_term_info(category: str, term_name: str) -> dict:
    """
    特定の用語詳細を取得
    """
    category_terms = TERMS_DATA.get(category, {})
    return category_terms.get(term_name, {})

