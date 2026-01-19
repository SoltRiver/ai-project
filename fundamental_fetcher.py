"""
ファンダメンタルデータ取得モジュール
財務・決算データ（PER、PBR、配当利回りなど）を取得して評価を付与する
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
import pandas as pd
import yfinance as yf

from analyzer import calculate_star_rating, format_stars
from data_fetcher import format_symbol_for_yfinance


def _parse_date_value(value: Any) -> Optional[datetime]:
    """yfinanceの値をdatetimeに変換する"""
    if value is None:
        return None
    if isinstance(value, (list, tuple)) and value:
        value = value[0]
    if hasattr(value, "to_pydatetime"):
        value = value.to_pydatetime()
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value)
        except Exception:
            return None
    if isinstance(value, datetime):
        return value
    return None


def fetch_fundamental_data(symbol: str) -> Optional[Dict[str, Any]]:
    """
    ファンダメンタルデータを取得
    """
    try:
        ticker = yf.Ticker(format_symbol_for_yfinance(symbol))
        info = ticker.info

        result = {
            "symbol": symbol,
            "per": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "pbr": info.get("priceToBook"),
            "dividend_yield": info.get("dividendYield"),
            "dividend_rate": info.get("dividendRate"),
            "debt_to_equity": info.get("debtToEquity"),
            "return_on_equity": info.get("returnOnEquity"),
            "return_on_assets": info.get("returnOnAssets"),
            "profit_margin": info.get("profitMargins"),
            "operating_margin": info.get("operatingMargins"),
            "current_ratio": info.get("currentRatio"),
            "quick_ratio": info.get("quickRatio"),
            "total_cash": info.get("totalCash"),
            "total_debt": info.get("totalDebt"),
            "total_revenue": info.get("totalRevenue"),
            "revenue_growth": info.get("revenueGrowth"),
            "earnings_growth": info.get("earningsGrowth"),
            "market_cap": info.get("marketCap"),
            "enterprise_value": info.get("enterpriseValue"),
            "book_value": info.get("bookValue"),
            "price_to_sales": info.get("priceToSalesTrailing12Months"),
            "peg_ratio": info.get("pegRatio"),
            "beta": info.get("beta"),
            "52_week_high": info.get("fiftyTwoWeekHigh"),
            "52_week_low": info.get("fiftyTwoWeekLow"),
            "average_volume": info.get("averageVolume"),
            "shares_outstanding": info.get("sharesOutstanding"),
            "float_shares": info.get("floatShares"),
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
            "exchange": info.get("exchange", ""),
            "currency": info.get("currency", "JPY"),
            "earnings_date": _parse_date_value(info.get("earningsDate") or info.get("earningsTimestamp")),
            "ex_dividend_date": _parse_date_value(info.get("exDividendDate") or info.get("nextDividendDate")),
        }

        # 自己資本比率を計算
        # 1. infoにequity_ratioがある場合（米国株など）
        if result.get("equity_ratio"):
            pass  # 既に値が入っている場合はそのまま
        # 2. totalAssetsとtotalStockholderEquityがinfoにある場合
        elif result.get("total_assets") and result.get("total_equity"):
             result["equity_ratio"] = (result["total_equity"] / result["total_assets"])
        # 3. balance_sheetから取得する場合（日本株など）
        else:
            try:
                bs = ticker.balance_sheet
                if not bs.empty:
                    # 最新のカラム（直近の決算）を取得
                    latest_date = bs.columns[0]
                    # pandasのSeriesとして取得
                    latest_data = bs[latest_date]
                    
                    total_assets = None
                    stockholders_equity = None

                    # Total Assetsの検索
                    if "Total Assets" in latest_data.index:
                        total_assets = latest_data["Total Assets"]
                    elif "TotalAssets" in latest_data.index:
                        total_assets = latest_data["TotalAssets"]
                    
                    # Stockholders Equityの検索
                    if "Stockholders Equity" in latest_data.index:
                        stockholders_equity = latest_data["Stockholders Equity"]
                    elif "Total Stockholder Equity" in latest_data.index:
                        stockholders_equity = latest_data["Total Stockholder Equity"]
                    elif "TotalEquity" in latest_data.index:
                        stockholders_equity = latest_data["TotalEquity"]

                    if total_assets and stockholders_equity and total_assets > 0:
                        result["equity_ratio"] = (stockholders_equity / total_assets)
            except Exception as e:
                print(f"バランスシートからの自己資本比率計算エラー: {e}")

        # フォールバック: 簡易計算 (Legacy logic)
        if result.get("equity_ratio") is None and result["total_debt"] and result["market_cap"]:
            total_equity = result["market_cap"] / result["pbr"] if result["pbr"] else None
            if total_equity:
                total_capital = result["total_debt"] + total_equity
                if total_capital > 0:
                    result["equity_ratio"] = (total_equity / total_capital)

        # Normalize dividend_yield (handle percentage vs ratio)
        if result.get("dividend_yield") is not None and result["dividend_yield"] > 0.5:
             # Assuming if > 0.5 (50%), it's a percentage value (e.g. 2.62 for 2.62%)
             # Normal yields are usually < 0.1 (10%)
             result["dividend_yield"] = result["dividend_yield"] / 100

        return result

    except Exception as e:
        print(f"ファンダメンタルデータ取得エラー: {e}")
        return None


def get_key_fundamentals(symbol: str) -> Optional[Dict[str, Any]]:
    """
    主要なファンダメンタル項目を取得（表示用）
    """
    data = fetch_fundamental_data(symbol)
    if data is None:
        return None

    key_indicators = {
        "PER": data.get("per"),
        "PBR": data.get("pbr"),
        "配当利回り": data.get("dividend_yield"),
        "自己資本比率": data.get("equity_ratio"),
        "市場区分": data.get("exchange"),
        "セクター": data.get("sector"),
        "業種": data.get("industry"),
        "ROE": data.get("return_on_equity"),
        "ROA": data.get("return_on_assets"),
        "利益率": data.get("profit_margin"),
        "earnings_date": data.get("earnings_date"),
        "ex_dividend_date": data.get("ex_dividend_date"),
        "beta": data.get("beta"),
        "revenue_growth": data.get("revenue_growth"),
        "earnings_growth": data.get("earnings_growth"),
        "dividend_rate": data.get("dividend_rate"),
        "average_volume": data.get("average_volume"),
    }
    return key_indicators


def format_fundamental_value(value: Any, format_type: str = "float") -> str:
    """
    ファンダメンタル値を表示用にフォーマット
    """
    if value is None:
        return "N/A"

    if format_type == "percent":
        if isinstance(value, (int, float)):
            return f"{value * 100:.2f}%"
        return str(value)

    if format_type == "currency":
        if isinstance(value, (int, float)):
            if abs(value) >= 1e12:
                return f"¥{value / 1e12:.2f}T"
            if abs(value) >= 1e9:
                return f"¥{value / 1e9:.2f}B"
            if abs(value) >= 1e6:
                return f"¥{value / 1e6:.2f}M"
            return f"¥{value:,.0f}"
        return str(value)

    if format_type == "float":
        if isinstance(value, (int, float)):
            return f"{value:.2f}"
        return str(value)

    return str(value)


def _status_for_lower_better(value: Optional[float],
                             good: float,
                             neutral: float,
                             unit: str = "") -> Dict[str, str]:
    """値が低いほど良い指標のステータス"""
    criteria = f"割安目安: {good}{unit}以下 / 標準: {neutral}{unit}以下"
    if value is None:
        return {"label": "N/A", "color": "gray", "criteria": criteria}
    if value <= good:
        return {"label": "割安", "color": "green", "criteria": criteria}
    if value <= neutral:
        return {"label": "標準", "color": "gray", "criteria": criteria}
    return {"label": "割高", "color": "red", "criteria": criteria}


def _status_for_higher_better(value: Optional[float],
                              great: float,
                              ok: float,
                              positive_label: str = "優良",
                              unit: str = "",
                              is_percent: bool = False) -> Dict[str, str]:
    """値が高いほど良い指標のステータス"""
    g_val = f"{great*100:.0f}%" if is_percent else f"{great}{unit}"
    o_val = f"{ok*100:.0f}%" if is_percent else f"{ok}{unit}"
    criteria = f"{positive_label}目安: {g_val}以上 / 標準: {o_val}以上"

    if value is None:
        return {"label": "N/A", "color": "gray", "criteria": criteria}
    if value >= great:
        return {"label": positive_label, "color": "green", "criteria": criteria}
    if value >= ok:
        return {"label": "標準", "color": "gray", "criteria": criteria}
    return {"label": "弱め", "color": "red", "criteria": criteria}


def get_fundamental_statuses(fundamental_data: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    """
    PERやPBRなどに評価ステータスを付与する
    """
    if fundamental_data is None:
        return {}

    per = fundamental_data.get("PER")
    pbr = fundamental_data.get("PBR")
    dividend_yield = fundamental_data.get("配当利回り")
    roe = fundamental_data.get("ROE")
    profit_margin = fundamental_data.get("利益率")
    equity_ratio = fundamental_data.get("自己資本比率")

    return {
        "PER": _status_for_lower_better(per, good=10, neutral=25, unit="倍"),
        "PBR": _status_for_lower_better(pbr, good=1, neutral=2, unit="倍"),
        "配当利回り": _status_for_higher_better(dividend_yield, great=0.04, ok=0.02, positive_label="優良", is_percent=True),
        "ROE": _status_for_higher_better(roe, great=0.1, ok=0.06, positive_label="優良", is_percent=True),
        "利益率": _status_for_higher_better(profit_margin, great=0.1, ok=0.05, positive_label="優良", is_percent=True),
        "自己資本比率": _status_for_higher_better(equity_ratio, great=0.4, ok=0.2, positive_label="安定", is_percent=True),
    }


def format_date(value: Optional[datetime]) -> str:
    """日付をYYYY-MM-DD形式に整える"""
    if value is None:
        return "N/A"
    try:
        return value.strftime("%Y-%m-%d")
    except Exception:
        return str(value)


def get_event_info(symbol: str, fundamental_data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    決算日・配当などの直近イベント情報を返す
    """
    data = fundamental_data or fetch_fundamental_data(symbol)
    if data is None:
        return None

    return {
        "earnings_date": data.get("earnings_date"),
        "ex_dividend_date": data.get("ex_dividend_date"),
        "dividend_yield": data.get("dividend_yield"),
        "dividend_rate": data.get("dividend_rate"),
        "has_shareholder_benefit": None,  # yfinanceでは取得しづらいため手動入力を想定
    }


def _average_stars(values: List[int]) -> int:
    """スター配列の平均を返す"""
    valid = [v for v in values if v is not None]
    if not valid:
        return 3
    return max(1, min(5, round(sum(valid) / len(valid))))


def _generate_score_reason(category: str, stars: int, metrics: Dict[str, Any]) -> str:
    """スコアの理由を生成する"""
    if stars >= 5:
        level = "極めて優秀"
    elif stars >= 4:
        level = "優秀"
    elif stars == 3:
        level = "標準的"
    elif stars == 2:
        level = "やや懸念"
    else:
        level = "要注意"

    if category == "安定性":
        equity = metrics.get('equity_ratio')
        beta = metrics.get('beta')
        reasons = []
        if equity:
            reasons.append(f"自己資本比率{equity:.1f}%")
        if beta:
            reasons.append(f"ベータ値{beta:.2f}")
        return f"財務基盤は{level}です。{'、'.join(reasons)}などから判断されます。"
    
    elif category == "成長性":
        rev = metrics.get('revenue_growth')
        earn = metrics.get('earnings_growth')
        reasons = []
        if rev:
            reasons.append(f"売上高成長率{rev*100:.1f}%")
        if earn:
            reasons.append(f"利益成長率{earn*100:.1f}%")
        if not reasons:
            return "成長データが不足しています。"
        return f"成長力は{level}です。{'、'.join(reasons)}などの推移です。"

    elif category == "割安度":
        per = metrics.get('PER')
        pbr = metrics.get('PBR')
        reasons = []
        if per:
            reasons.append(f"PER {per:.1f}倍")
        if pbr:
            reasons.append(f"PBR {pbr:.1f}倍")
        return f"株価水準は{level}です。{'、'.join(reasons)}となっています。"

    elif category == "配当魅力度":
        div = metrics.get('配当利回り')
        if div:
            return f"配当水準は{level}です。利回りは{div*100:.2f}%となっています。"
        return "配当データがありません（無配の可能性があります）。"

    return ""


def build_company_scores(fundamental_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    安定性・成長性・割安度・配当魅力度の★評価を返す
    """
    if fundamental_data is None:
        return {}

    per = fundamental_data.get("PER")
    pbr = fundamental_data.get("PBR")
    beta = fundamental_data.get("beta")
    dividend_yield = fundamental_data.get("配当利回り")
    equity_ratio = fundamental_data.get("自己資本比率")
    revenue_growth = fundamental_data.get("revenue_growth")
    earnings_growth = fundamental_data.get("earnings_growth")

    stability = _average_stars([
        calculate_star_rating(beta, [1.5, 1.2, 1.0, 0.8], reverse=True),
        calculate_star_rating(equity_ratio, [20, 30, 40, 50], reverse=False),
    ])
    stability_reason = _generate_score_reason("安定性", stability, {"equity_ratio": equity_ratio, "beta": beta})

    growth = _average_stars([
        calculate_star_rating(revenue_growth, [0.0, 0.05, 0.1, 0.15]),
        calculate_star_rating(earnings_growth, [0.0, 0.05, 0.1, 0.15]),
    ])
    growth_reason = _generate_score_reason("成長性", growth, {"revenue_growth": revenue_growth, "earnings_growth": earnings_growth})

    valuation = _average_stars([
        calculate_star_rating(per, [25, 20, 15, 10], reverse=True),
        calculate_star_rating(pbr, [2.5, 2.0, 1.5, 1.0], reverse=True),
    ])
    valuation_reason = _generate_score_reason("割安度", valuation, {"PER": per, "PBR": pbr})

    dividend = calculate_star_rating(dividend_yield, [0.01, 0.02, 0.04, 0.06])
    dividend_reason = _generate_score_reason("配当魅力度", dividend, {"配当利回り": dividend_yield})

    return {
        "安定性": {"stars": stability, "display": format_stars(stability), "reason": stability_reason},
        "成長性": {"stars": growth, "display": format_stars(growth), "reason": growth_reason},
        "割安度": {"stars": valuation, "display": format_stars(valuation), "reason": valuation_reason},
        "配当魅力度": {"stars": dividend, "display": format_stars(dividend), "reason": dividend_reason},
    }
