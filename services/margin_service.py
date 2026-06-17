"""
需給タブ用サービスモジュール

信用取引残高データから需給サイズ・構成比・偏り・信頼度を算出する。
価格予測に見える表現は一切使用しない。
"""

import logging
import statistics
from typing import Any, Dict, List, Optional

from services.jquants_client import client as jquants_client
from services.data_fetcher import fetch_stock_data, format_symbol_for_yfinance

logger = logging.getLogger(__name__)

# ─── 定数（閾値） ────────────────────────────────────
# 需給サイズ分類の閾値（total / ADV20 の日数）
SIZE_THRESHOLD_LOW = 1  # days < 1 → 低
SIZE_THRESHOLD_HIGH = 5  # days >= 5 → 高

# 偏り分類の閾値（buy / sell の比率）
BIAS_STRONG_BUY = 3.0  # ratio >= 3.0 → 買い偏り（強）
BIAS_WEAK_BUY = 1.5  # 1.5 <= ratio < 3.0 → 買い偏り（弱）
BIAS_NEUTRAL_LOW = 0.8  # 0.8 <= ratio < 1.5 → 偏りなし
BIAS_WEAK_SELL = 0.5  # 0.5 <= ratio < 0.8 → 売り偏り（弱）
# ratio < 0.5 → 売り偏り（強）

# 売り残が極端に小さいと判断する閾値（株数）
SELL_MINIMUM_THRESHOLD = 100

# 出来高外れ値クリップ倍率（中央値の N 倍を上限）
OUTLIER_MULTIPLIER = 3

# ADV算出に必要な最低取引日数
ADV_MIN_DAYS = 20


def get_margin_tab(code: str) -> Dict[str, Any]:
    """
    需給タブ用の全データを構築して返す。

    Returns:
        テンプレートに渡す辞書。
        エラー発生時もフォールバックデータを返す。
    """
    result = {
        "margin_available": False,
        "error_message": None,
    }

    try:
        # 1. 信用残データ取得
        margin_data = _fetch_margin_data(code)
        if not margin_data:
            result["error_message"] = "信用残データを取得できませんでした"
            result["margin"] = _empty_margin_data()
            return result

        latest = margin_data[0]
        previous = margin_data[1] if len(margin_data) >= 2 else None

        # 2. 買い残・売り残を取得
        buy = _safe_int(
            latest.get("SellMarginTradeVolume")
        )  # 注意: J-Quants のキー名確認
        sell = _safe_int(latest.get("BuyMarginTradeVolume"))

        # J-Quants v2 のレスポンスキー名に合わせる
        # margin-interest のキー: MarginBuyingBalance, MarginSellingBalance 等
        # 正確なキー名を使用
        buy = _safe_int(
            latest.get("MarginBuyingBalance")
            or latest.get("MarginBuyNewVolume")
            or latest.get("margin_buy_balance")
            or latest.get("SellMarginTradeVolume")
            or 0
        )
        sell = _safe_int(
            latest.get("MarginSellingBalance")
            or latest.get("MarginSellNewVolume")
            or latest.get("margin_sell_balance")
            or latest.get("BuyMarginTradeVolume")
            or 0
        )

        # もしどちらも0なら、別のキー名を試す
        if buy == 0 and sell == 0:
            # キー名のログ出力（デバッグ用）
            logger.info(f"需給データキー一覧: {list(latest.keys())}")
            # 全キーを探索して残高っぽいものを探す
            for key, val in latest.items():
                logger.info(f"  {key}: {val}")

        total = buy + sell
        date_str = latest.get("Date", "-")

        # 3. 前週データの取得
        prev_buy = 0
        prev_sell = 0
        if previous:
            prev_buy = _safe_int(
                previous.get("MarginBuyingBalance")
                or previous.get("MarginBuyNewVolume")
                or previous.get("margin_buy_balance")
                or previous.get("SellMarginTradeVolume")
                or 0
            )
            prev_sell = _safe_int(
                previous.get("MarginSellingBalance")
                or previous.get("MarginSellNewVolume")
                or previous.get("margin_sell_balance")
                or previous.get("BuyMarginTradeVolume")
                or 0
            )

        delta_buy = buy - prev_buy
        delta_sell = sell - prev_sell

        # 4. ADV20 算出
        adv20, data_days = _calc_adv20(code)

        # 5. 需給サイズ算出
        size_info = _calc_supply_demand_size(total, adv20, data_days)

        # 6. 構成比算出
        if total > 0:
            buy_pct = round(buy / total * 100, 1)
            sell_pct = round(100 - buy_pct, 1)
        else:
            buy_pct = 0.0
            sell_pct = 0.0

        # 7. 前週比算出
        week_change_buy = _calc_week_change(buy, prev_buy)
        week_change_sell = _calc_week_change(sell, prev_sell)

        # 8. 偏り分類
        bias_info = _calc_bias(buy, sell, delta_buy, delta_sell)

        # 9. 信頼度
        reliability = _calc_reliability(buy, sell, adv20, data_days, bias_info["label"])

        result["margin_available"] = True
        result["margin"] = {
            "date": date_str,
            # 需給サイズ
            "size_label": size_info["label"],
            "size_days": size_info["days"],
            "size_reason": size_info.get("reason", ""),
            # 構成比
            "buy": buy,
            "sell": sell,
            "total": total,
            "buy_pct": buy_pct,
            "sell_pct": sell_pct,
            # 前週比
            "week_change_buy": week_change_buy,
            "week_change_sell": week_change_sell,
            "has_previous": previous is not None,
            # 偏り
            "bias_label": bias_info["label"],
            "bias_css": bias_info["css"],
            "bias_reason": bias_info.get("reason", ""),
            # 信頼度
            "reliability_label": reliability["label"],
            "reliability_icon": reliability["icon"],
            "reliability_css": reliability["css"],
        }

    except Exception as e:
        logger.error(f"需給データ構築エラー ({code}): {e}", exc_info=True)
        result["error_message"] = "需給データの処理中にエラーが発生しました"
        result["margin"] = _empty_margin_data()

    return result


def _fetch_margin_data(code: str) -> List[Dict[str, Any]]:
    """J-Quants API から信用残データを取得する"""
    try:
        data = jquants_client.get_margin_interest(code)
        return data if data else []
    except Exception as e:
        logger.error(f"信用残データ取得エラー ({code}): {e}")
        return []


def _calc_adv20(code: str) -> tuple:
    """
    yfinance から20日平均出来高（ADV20）を算出する。
    外れ値対策: 中央値の3倍を超える出来高は上限クリップ。

    Returns:
        (adv20: float or None, data_days: int)
        adv20 が算出不可の場合は (None, 0)
    """
    try:
        symbol = format_symbol_for_yfinance(code)
        # 約2ヶ月分を取得（祝日・休場を考慮して多めに取得）
        df = fetch_stock_data(symbol, period="2mo", interval="1d")
        if df is None or df.empty:
            return None, 0

        # 出来高カラムを取得
        vol_col = "volume" if "volume" in df.columns else "Volume"
        if vol_col not in df.columns:
            return None, 0

        volumes = df[vol_col].dropna().tolist()
        if not volumes:
            return None, 0

        data_days = len(volumes)

        # 外れ値対策: 中央値の3倍を超える出来高は上限クリップ
        median_vol = statistics.median(volumes)
        clip_threshold = median_vol * OUTLIER_MULTIPLIER
        clipped_volumes = [min(v, clip_threshold) for v in volumes]

        # 直近20日分を使用（20日未満の場合はある分だけ使用）
        recent_volumes = clipped_volumes[-ADV_MIN_DAYS:]
        adv20 = sum(recent_volumes) / len(recent_volumes) if recent_volumes else None

        return adv20, min(data_days, ADV_MIN_DAYS)

    except Exception as e:
        logger.error(f"ADV20算出エラー ({code}): {e}")
        return None, 0


def _calc_supply_demand_size(
    total: int, adv20: Optional[float], data_days: int
) -> Dict[str, Any]:
    """
    需給サイズ（相対）を算出する。

    Returns:
        {"label": str, "days": str, "reason": str}
    """
    # 例外処理1: ADV が欠損 / 0
    if adv20 is None or adv20 <= 0:
        return {
            "label": "未判定",
            "days": "-",
            "reason": "出来高データが取得できないため未判定です",
        }

    days = total / adv20

    # 例外処理2: データ日数が20日未満
    if data_days < ADV_MIN_DAYS:
        # 分類はするが「暫定」扱い
        size_label = _classify_size(days) + "（暫定）"
        return {
            "label": size_label,
            "days": f"{days:.1f}",
            "reason": "データ日数が少ないため暫定評価です",
        }

    # 通常の分類
    return {
        "label": _classify_size(days),
        "days": f"{days:.1f}",
        "reason": "",
    }


def _classify_size(days: float) -> str:
    """日数から需給サイズを分類する"""
    if days < SIZE_THRESHOLD_LOW:
        return "低"
    elif days < SIZE_THRESHOLD_HIGH:
        return "中"
    else:
        return "高"


def _calc_bias(buy: int, sell: int, delta_buy: int, delta_sell: int) -> Dict[str, Any]:
    """
    偏り分類（5段階）を算出する。

    Returns:
        {"label": str, "css": str, "reason": str}
    """
    # 例外: 売り残が極端に小さい場合
    if sell < SELL_MINIMUM_THRESHOLD:
        return {
            "label": "判定保留",
            "css": "bias-pending",
            "reason": "売り残が極端に小さいため倍率が参考になりにくい",
        }

    ratio = buy / sell

    # 買い偏り（強）: ratio >= 3.0 AND delta_buy > 0 AND delta_sell <= 0
    if ratio >= BIAS_STRONG_BUY and delta_buy > 0 and delta_sell <= 0:
        return {"label": "買い偏り（強）", "css": "bias-strong-buy", "reason": ""}

    # 買い偏り（弱）: 1.5 <= ratio < 3.0 AND delta_buy >= 0
    if BIAS_WEAK_BUY <= ratio < BIAS_STRONG_BUY and delta_buy >= 0:
        return {"label": "買い偏り（弱）", "css": "bias-weak-buy", "reason": ""}

    # 偏りなし: 0.8 <= ratio < 1.5
    if BIAS_NEUTRAL_LOW <= ratio < BIAS_WEAK_BUY:
        return {"label": "偏りなし", "css": "bias-neutral", "reason": ""}

    # 売り偏り（弱）: 0.5 <= ratio < 0.8 AND delta_sell >= 0
    if BIAS_WEAK_SELL <= ratio < BIAS_NEUTRAL_LOW and delta_sell >= 0:
        return {"label": "売り偏り（弱）", "css": "bias-weak-sell", "reason": ""}

    # 売り偏り（強）: ratio < 0.5 AND delta_sell > 0 AND delta_buy <= 0
    if ratio < BIAS_WEAK_SELL and delta_sell > 0 and delta_buy <= 0:
        return {"label": "売り偏り（強）", "css": "bias-strong-sell", "reason": ""}

    # 上記のどれにも該当しない場合（中間的なケース）
    # ratio に基づいて最も近いカテゴリに分類
    if ratio >= BIAS_STRONG_BUY:
        return {"label": "買い偏り（強）", "css": "bias-strong-buy", "reason": ""}
    elif ratio >= BIAS_WEAK_BUY:
        return {"label": "買い偏り（弱）", "css": "bias-weak-buy", "reason": ""}
    elif ratio >= BIAS_NEUTRAL_LOW:
        return {"label": "偏りなし", "css": "bias-neutral", "reason": ""}
    elif ratio >= BIAS_WEAK_SELL:
        return {"label": "売り偏り（弱）", "css": "bias-weak-sell", "reason": ""}
    else:
        return {"label": "売り偏り（強）", "css": "bias-strong-sell", "reason": ""}


def _calc_reliability(
    buy: int, sell: int, adv20: Optional[float], data_days: int, bias_label: str
) -> Dict[str, Any]:
    """
    信頼度評価を算出する。
    分類の安定度を示すものであり、予測ではない。

    Returns:
        {"label": str, "icon": str, "css": str}
    """
    # 未確定条件
    if buy == 0 and sell == 0:
        return {"label": "未確定", "icon": "—", "css": "reliability-unknown"}
    if adv20 is None or adv20 <= 0:
        return {"label": "未確定", "icon": "—", "css": "reliability-unknown"}
    if bias_label == "判定保留":
        return {"label": "低", "icon": "△", "css": "reliability-low"}

    # データ日数が不足 → 低
    if data_days < ADV_MIN_DAYS:
        return {"label": "低", "icon": "△", "css": "reliability-low"}

    # 売り残が比較的小さい → 中
    if sell < 1000:
        return {"label": "中", "icon": "〇", "css": "reliability-mid"}

    # 十分なデータがあり安定 → 高
    return {"label": "高", "icon": "◎", "css": "reliability-high"}


def _calc_week_change(current: int, previous: int) -> Dict[str, Any]:
    """
    前週比を算出する。

    Returns:
        {"delta": str, "pct": str, "direction": str}
    """
    if previous == 0:
        return {"delta": "-", "pct": "-", "direction": "flat"}

    delta = current - previous
    pct = (delta / previous) * 100

    if delta > 0:
        direction = "up"
        delta_str = f"+{delta:,}"
        pct_str = f"+{pct:.1f}%"
    elif delta < 0:
        direction = "down"
        delta_str = f"{delta:,}"
        pct_str = f"{pct:.1f}%"
    else:
        direction = "flat"
        delta_str = "±0"
        pct_str = "0.0%"

    return {"delta": delta_str, "pct": pct_str, "direction": direction}


def _safe_int(value: Any) -> int:
    """安全に整数変換する。変換できない場合は 0 を返す"""
    if value is None:
        return 0
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _empty_margin_data() -> Dict[str, Any]:
    """データなし時のフォールバック用空辞書"""
    return {
        "date": "-",
        "size_label": "未判定",
        "size_days": "-",
        "size_reason": "データが取得できませんでした",
        "buy": 0,
        "sell": 0,
        "total": 0,
        "buy_pct": 0.0,
        "sell_pct": 0.0,
        "week_change_buy": {"delta": "-", "pct": "-", "direction": "flat"},
        "week_change_sell": {"delta": "-", "pct": "-", "direction": "flat"},
        "has_previous": False,
        "bias_label": "未判定",
        "bias_css": "bias-pending",
        "bias_reason": "データが取得できませんでした",
        "reliability_label": "未確定",
        "reliability_icon": "—",
        "reliability_css": "reliability-unknown",
    }
