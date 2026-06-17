import yfinance as yf
import pandas as pd
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from services.ai_client import get_gemini_model, get_ai_client
import google.generativeai as genai

# ランキング母集団 (日経225採用銘柄を中心とした主要銘柄)
# パフォーマンスのため、一旦100銘柄程度に絞る。コードはyfinance形式
RANKING_UNIVERSE = [
    "7203.T",
    "6758.T",
    "9984.T",
    "8306.T",
    "8035.T",
    "6098.T",
    "4063.T",
    "6861.T",
    "4502.T",
    "8316.T",
    "9432.T",
    "9433.T",
    "6501.T",
    "6954.T",
    "7741.T",
    "4519.T",
    "7974.T",
    "8001.T",
    "8031.T",
    "6367.T",
    "6702.T",
    "6981.T",
    "4568.T",
    "6273.T",
    "7267.T",
    "8058.T",
    "9022.T",
    "4901.T",
    "6178.T",
    "8766.T",
    "6503.T",
    "4661.T",
    "6902.T",
    "4452.T",
    "3382.T",
    "6723.T",
    "7733.T",
    "4503.T",
    "2914.T",
    "6762.T",
    "6506.T",
    "6301.T",
    "8801.T",
    "8802.T",
    "9020.T",
    "9101.T",
    "9104.T",
    "9107.T",
    "9201.T",
    "9202.T",
    "2802.T",
    "2502.T",
    "2503.T",
    "3407.T",
    "3402.T",
    "4188.T",
    "4005.T",
    "5108.T",
    "5401.T",
    "5411.T",
    "5713.T",
    "5802.T",
    "6326.T",
    "6471.T",
    "6473.T",
    "6594.T",
    "6645.T",
    "6752.T",
    "6857.T",
    "6971.T",
    "6976.T",
    "7011.T",
    "7012.T",
    "7201.T",
    "7261.T",
    "7269.T",
    "7270.T",
    "7272.T",
    "4523.T",
    "4543.T",
    "4578.T",
    "4689.T",
    "4755.T",
    "4911.T",
    "1605.T",
    "1925.T",
    "1928.T",
    "1801.T",
    "1802.T",
    "1803.T",
    "1812.T",
    "3092.T",
    "3099.T",
    "8267.T",
    "8308.T",
    "8309.T",
    "8316.T",
    "8411.T",
    "8601.T",
    "8604.T",
]

# 銘柄名の日本語マッピング (yfinanceが英語名を返す場合の補完用)
JP_STOCK_NAME_MAP = {
    "7203": "トヨタ自動車",
    "6758": "ソニーグループ",
    "9984": "ソフトバンクグループ",
    "8306": "三菱UFJフィナンシャルG",
    "8035": "東京エレクトロン",
    "6098": "リクルートHD",
    "4063": "信越化学工業",
    "6861": "キーエンス",
    "4502": "武田薬品工業",
    "8316": "三井住友フィナンシャルG",
    "9432": "日本電信電話(NTT)",
    "9433": "KDDI",
    "6501": "日立製作所",
    "6954": "ファナック",
    "7741": "HOYA",
    "4519": "中外製薬",
    "7974": "任天堂",
    "8001": "伊藤忠商事",
    "8031": "三井物産",
    "6367": "ダイキン工業",
    "6702": "富士通",
    "6981": "村田製作所",
    "4568": "第一三共",
    "6273": "SMC",
    "7267": "本田技研工業",
    "8058": "三菱商事",
    "9022": "東海旅客鉄道",
    "4901": "富士フイルムHD",
    "6178": "日本郵政",
    "8766": "東京海上HD",
    "6503": "三菱電機",
    "4661": "オリエンタルランド",
    "6902": "デンソー",
    "4452": "花王",
    "3382": "セブン&アイHD",
    "6723": "ルネサスエレクトロニクス",
    "7733": "オリンパス",
    "4503": "アステラス製薬",
    "2914": "日本たばこ産業(JT)",
    "6762": "TDK",
    "6506": "安川電機",
    "6301": "小松製作所",
    "8801": "三井不動産",
    "8802": "三菱地所",
    "9020": "東日本旅客鉄道",
    "9101": "日本郵船",
    "9104": "商船三井",
    "9107": "川崎汽船",
    "9201": "日本航空(JAL)",
    "9202": "ANA HD",
    "2802": "味の素",
    "2502": "アサヒグループHD",
    "2503": "キリンHD",
    "3407": "旭化成",
    "3402": "東レ",
    "4188": "三菱ケミカルグループ",
    "4005": "住友化学",
    "5108": "ブリヂストン",
    "5401": "日本製鉄",
    "5411": "JFE HD",
    "5713": "住友金属鉱山",
    "5802": "住友電気工業",
    "6326": "クボタ",
    "6471": "日本精工",
    "6473": "ジェイテクト",
    "6594": "ニデック",
    "6645": "オムロン",
    "6752": "パナソニックHD",
    "6857": "アドバンテスト",
    "6971": "京セラ",
    "6976": "太陽誘電",
    "7011": "三菱重工業",
    "7012": "川崎重工業",
    "7201": "日産自動車",
    "7261": "マツダ",
    "7269": "スズキ",
    "7270": "SUBARU",
    "7272": "ヤマハ発動機",
    "4523": "エーザイ",
    "4543": "テルモ",
    "4578": "大塚HD",
    "4689": "LINEヤフー",
    "4755": "楽天グループ",
    "4911": "資生堂",
    "1605": "INPEX",
    "1925": "大和ハウス工業",
    "1928": "積水ハウス",
    "1801": "大成建設",
    "1802": "大林組",
    "1803": "清水建設",
    "1812": "鹿島建設",
    "3092": "ZOZO",
    "3099": "三越伊勢丹HD",
    "8267": "イオン",
    "8308": "りそなHD",
    "8309": "三井住友トラストHD",
    "8411": "みずほフィナンシャルG",
    "8601": "大和証券グループ本社",
    "8604": "野村HD",
}

# セクターの日本語翻訳マップ
SECTOR_MAP = {
    "Technology": "テクノロジー",
    "Financial Services": "金融",
    "Healthcare": "ヘルスケア",
    "Consumer Cyclical": "一般消費財",
    "Consumer Defensive": "生活必需品",
    "Industrials": "資本財",
    "Basic Materials": "素材",
    "Energy": "エネルギー",
    "Utilities": "公共事業",
    "Real Estate": "不動産",
    "Communication Services": "通信サービス",
}


def fetch_ranking_data(period_type: str = "today") -> List[Dict[str, Any]]:
    """
    主要銘柄の騰落率ランキング用データを一括取得・計算する
    """
    days_map = {
        "today": 7,  # 前日比取得のため少し余分に (土日祝考慮)
        "week": 14,
        "month": 45,
        "year": 400,
    }
    target_days = {"today": 1, "week": 5, "month": 20, "year": 252}

    needed_days = days_map.get(period_type, 5)
    start_date = (datetime.now() - timedelta(days=needed_days)).strftime("%Y-%m-%d")

    # yfinanceで一括取得 (高速化)
    try:
        data = yf.download(
            RANKING_UNIVERSE,
            start=start_date,
            interval="1d",
            group_by="ticker",
            threads=True,
        )
        if data.empty:
            return []
    except Exception as e:
        print(f"ランキングデータ取得エラー: {e}")
        return []

    results = []
    for ticker in RANKING_UNIVERSE:
        try:
            if ticker not in data.columns.levels[0]:
                continue

            df = data[ticker].dropna()
            if len(df) < 2:
                continue

            # 期間に応じた変化率計算
            current_price = float(df["Close"].iloc[-1])

            # 指定された営業日前の価格を取得
            offset = target_days.get(period_type, 1)
            if len(df) > offset:
                base_price = float(df["Close"].iloc[-(offset + 1)])
            else:
                base_price = float(df["Close"].iloc[0])

            change = current_price - base_price
            change_percent = (change / base_price) * 100

            # yfinanceのticker.infoは遅いので、社名はとりあえずコードから (後でマップ化検討)
            results.append(
                {
                    "symbol": ticker.replace(".T", ""),
                    "full_symbol": ticker,
                    "name": ticker,  # 仮設定。後で詳細取得時に補完
                    "price": current_price,
                    "change": change,
                    "change_percent": change_percent,
                    "sector": "不明",  # 仮
                }
            )
        except:
            continue

    return results


def get_rankings(
    period_type: str = "today", limit: int = 10, target_type: Optional[str] = None
) -> Dict[str, List[Dict[str, Any]]]:
    """
    上昇率・下落率ランキングを取得する
    """
    all_data = fetch_ranking_data(period_type)
    if not all_data:
        return {"top": [], "bottom": []}

    # NaNや異常値があれば排除 (念のため)
    all_data = [x for x in all_data if pd.notnull(x["change_percent"])]

    if not all_data:
        return {"top": [], "bottom": []}

    # 取得したいタイプが明確な場合は片方だけ計算
    top = []
    bottom = []

    if target_type is None or target_type == "top":
        top = sorted(
            all_data, key=lambda x: (x["change_percent"], x["change"]), reverse=True
        )[:limit]

    if target_type is None or target_type == "bottom":
        bottom = sorted(all_data, key=lambda x: (x["change_percent"], x["change"]))[
            :limit
        ]

    def enrich_info(rank_list):
        if not rank_list:
            return []
        for item in rank_list:
            symbol_only = item["symbol"]
            # マッピングにある場合はそれを使う (高速化)
            if symbol_only in JP_STOCK_NAME_MAP:
                item["name"] = JP_STOCK_NAME_MAP[symbol_only]
                # セクター情報を既知のものから推測、または最小限の取得
                if item.get("sector") == "不明":
                    # 一旦セクターなしでも名前があれば十分な場合が多いが、
                    # ユーザー満足度向上のため、もし info が必要ならここでのみ呼ぶ
                    # (ただし10個以上は重いので、上位のみにするなどの配慮が必要)
                    pass
                item["reason"] = f"市場動向や個別材料による騰落が考えられます。"
                continue

            # マッピングにない場合のみ yfinance に問い合わせ
            try:
                t = yf.Ticker(item["full_symbol"])
                # .info 呼び出しを最小限にするため、必要最低限のキーだけ取得したいが
                # yfinanceのTicker.infoは全体をフェッチするので注意
                info = t.info
                item["name"] = (
                    info.get("longName") or info.get("shortName") or symbol_only
                )
                raw_sector = info.get("sector", "不明")
                item["sector"] = SECTOR_MAP.get(raw_sector, raw_sector)
                item["reason"] = f"{item['sector']}セクターの動きによる騰落。"
            except:
                pass
        return rank_list

    return {"top": enrich_info(top), "bottom": enrich_info(bottom)}


def analyze_ranking_with_ai(rank_items: List[Dict[str, Any]], is_top: bool) -> str:
    """
    ランキングの傾向をAIで分析する
    """
    if not rank_items:
        return "分析対象のデータがありません。"

    type_str = "上昇" if is_top else "下落"
    rank_text = ""
    for idx, item in enumerate(rank_items):
        rank_text += f"{idx+1}位: {item['name']} ({item['symbol']}) - {item['change_percent']:.2f}% | セクター: {item['sector']}\n"

    prompt = f"""
以下の日本の株式市場における{type_str}率ランキングTOP10のデータを分析し、市場の傾向を解説してください。

【ランキングデータ】
{rank_text}

【依頼内容】
以下の3点を必ず含めて、箇条書きで簡潔に（全体で3～5行程度に）まとめてください。
・ランクインしている銘柄の特徴
・目立つセクター
・影響があると想定される出来事や背景

【出力ルール】
・必ず日本語で回答してください。
・「***」や「###」などのマークダウン装飾、太字、見出し記法は一切使用しないでください。
・純粋なテキストのみを出力してください。
・文末に「※本情報は投資勧誘を目的としたものではなく、投資の最終判断はご自身で行ってください。」という注意書きを必ず含めてください。
"""

    def clean_markdown(text: str) -> str:
        """マークダウンと思われる記号を除去する"""
        chars_to_remove = ["*", "#", "_", "`", ">"]
        for char in chars_to_remove:
            text = text.replace(char, "")
        return text.strip()

    # 1. Gemini を試行
    model = get_gemini_model("gemini-flash-latest")
    if model:
        try:
            response = model.generate_content(prompt)
            return clean_markdown(response.text)
        except Exception as e:
            print(f"Geminiランキング分析エラー: {e}")

    # 2. OpenAI フォールバック
    client = get_ai_client()
    if client:
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "あなたは熟練した証券アナリストです。装飾記号を使わず、プレーンテキストのみで回答してください。",
                    },
                    {"role": "user", "content": prompt},
                ],
            )
            return clean_markdown(response.choices[0].message.content)
        except Exception as e:
            print(f"OpenAIランキング分析エラー: {e}")

    return "AI分析は現在利用できません。セクター別の傾向などをご確認ください。"
