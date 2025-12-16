"""
ファンダメンタルデータ取得モジュール
財務・決算データ（PER、PBR、配当利回りなど）を取得して評価を付与する
"""

from datetime import datetime
from typing import Optional, Dict, Any, List

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

        # 自己資本比率を計算（可能な場合）
        if result["total_debt"] and result["market_cap"]:
            total_equity = result["market_cap"] / result["pbr"] if result["pbr"] else None
            if total_equity:
                total_capital = result["total_debt"] + total_equity
                if total_capital > 0:
                    result["equity_ratio"] = (total_equity / total_capital) * 100
                else:
                    result["equity_ratio"] = None
            else:
                result["equity_ratio"] = None
        else:
            result["equity_ratio"] = None

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
                             neutral: float) -> Dict[str, str]:
    """値が低いほど良い指標のステータス"""
    if value is None:
        return {"label": "N/A", "color": "gray"}
    if value <= good:
        return {"label": "割安", "color": "green"}
    if value <= neutral:
        return {"label": "標準", "color": "gray"}
    return {"label": "割高", "color": "red"}


def _status_for_higher_better(value: Optional[float],
                              great: float,
                              ok: float,
                              positive_label: str = "優良") -> Dict[str, str]:
    """値が高いほど良い指標のステータス"""
    if value is None:
        return {"label": "N/A", "color": "gray"}
    if value >= great:
        return {"label": positive_label, "color": "green"}
    if value >= ok:
        return {"label": "標準", "color": "gray"}
    return {"label": "弱め", "color": "red"}


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

    return {
        "PER": _status_for_lower_better(per, good=10, neutral=25),
        "PBR": _status_for_lower_better(pbr, good=1, neutral=2),
        "配当利回り": _status_for_higher_better(dividend_yield, great=0.04, ok=0.02, positive_label="優良"),
        "ROE": _status_for_higher_better(roe, great=0.1, ok=0.06, positive_label="優良"),
        "利益率": _status_for_higher_better(profit_margin, great=0.1, ok=0.05, positive_label="優良"),
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

    growth = _average_stars([
        calculate_star_rating(revenue_growth, [0.0, 0.05, 0.1, 0.15]),
        calculate_star_rating(earnings_growth, [0.0, 0.05, 0.1, 0.15]),
    ])

    valuation = _average_stars([
        calculate_star_rating(per, [25, 20, 15, 10], reverse=True),
        calculate_star_rating(pbr, [2.5, 2.0, 1.5, 1.0], reverse=True),
    ])

    dividend = calculate_star_rating(dividend_yield, [0.01, 0.02, 0.04, 0.06])

    return {
        "安定性": {"stars": stability, "display": format_stars(stability)},
        "成長性": {"stars": growth, "display": format_stars(growth)},
        "割安度": {"stars": valuation, "display": format_stars(valuation)},
        "配当魅力度": {"stars": dividend, "display": format_stars(dividend)},
    }
