"""
株価データ取得モジュール
外部API（yfinance）から株価データや情報を取得する
"""

from datetime import datetime
from typing import Optional, Dict, Any, List

import pandas as pd
import yfinance as yf


def fetch_stock_data(
    symbol: str, period: str = "1mo", interval: str = "1d"
) -> Optional[pd.DataFrame]:
    """
    yfinanceを使用して株価データを取得する
    """
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)

        if df.empty:
            return None

        df.columns = [col.lower() for col in df.columns]
        df = df.reset_index()

        if "Date" in df.columns:
            df = df.rename(columns={"Date": "date"})
        elif "Datetime" in df.columns:
            df = df.rename(columns={"Datetime": "date"})

        return df

    except Exception as e:
        print(f"データ取得エラー: {e}")
        return None


def fetch_stock_info(symbol: str) -> Optional[Dict[str, Any]]:
    """
    銘柄の基本情報（価格・出来高など）を取得する
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        result = {
            "symbol": symbol,
            "name": info.get("longName") or info.get("shortName", ""),
            "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
            "previous_close": info.get("previousClose"),
            "volume": info.get("volume") or info.get("regularMarketVolume"),
            "average_volume": info.get("averageVolume"),
            "market_cap": info.get("marketCap"),
            "shares_outstanding": info.get("sharesOutstanding"),
            "dividend_yield": info.get("dividendYield"),
            # PER・PBR（株価リスト表示用）
            "trailing_pe": info.get("trailingPE"),
            "price_to_book": info.get("priceToBook"),
            "currency": info.get("currency", "JPY"),
            "exchange": info.get("exchange", ""),
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
            # Financials for fallback
            "total_revenue": info.get("totalRevenue"),
            "net_income": info.get("netIncomeToCommon"),
            "operating_margins": info.get("operatingMargins"),
            "return_on_assets": info.get("returnOnAssets"),
            "return_on_equity": info.get("returnOnEquity"),
            "book_value": info.get("bookValue"),
            "shares_outstanding": info.get("sharesOutstanding"),
            "operating_cashflow": info.get("operatingCashflow"),
            "free_cashflow": info.get("freeCashflow"),
        }

        if result["current_price"] and result["previous_close"]:
            change = result["current_price"] - result["previous_close"]
            change_percent = (change / result["previous_close"]) * 100
            result["change"] = change
            result["change_percent"] = change_percent
        else:
            result["change"] = None
            result["change_percent"] = None

        return result

    except Exception as e:
        print(f"銘柄情報取得エラー: {e}")
        return None


def format_symbol_for_yfinance(symbol: str) -> str:
    """
    日本の銘柄コードをyfinance形式に変換
    """
    if symbol.endswith(".T"):
        return symbol
    if symbol.isdigit() and len(symbol) == 4:
        return f"{symbol}.T"
    return symbol


def get_latest_price(symbol: str) -> Optional[float]:
    """
    最新の株価を取得する
    """
    try:
        ticker = yf.Ticker(format_symbol_for_yfinance(symbol))
        data = ticker.history(period="1d", interval="1d")

        if data.empty:
            return None

        return float(data["Close"].iloc[-1])

    except Exception as e:
        print(f"最新価格取得エラー: {e}")
        return None


def fetch_realtime_data(symbol: str) -> Optional[Dict[str, Any]]:
    """
    最新のOHLCと出来高を取得する
    """
    try:
        ticker = yf.Ticker(format_symbol_for_yfinance(symbol))
        data = ticker.history(period="1d", interval="1d")

        if data.empty:
            return None

        latest = data.iloc[-1]

        return {
            "date": data.index[-1],
            "open": float(latest["Open"]),
            "high": float(latest["High"]),
            "low": float(latest["Low"]),
            "close": float(latest["Close"]),
            "volume": int(latest["Volume"]) if "Volume" in latest else None,
        }

    except Exception as e:
        print(f"リアルタイムデータ取得エラー: {e}")
        return None


def fetch_stock_history_periods(
    symbol: str, periods: Optional[Dict[str, tuple[str, str]]] = None
) -> Dict[str, Optional[pd.DataFrame]]:
    """
    指定した複数期間の株価履歴をまとめて取得する
    """
    if periods is None:
        periods = {
            "1年": ("1y", "1wk"),
            "5年": ("5y", "1mo"),
            "10年": ("10y", "1mo"),
        }

    history: Dict[str, Optional[pd.DataFrame]] = {}
    for label, (period, interval) in periods.items():
        history[label] = fetch_stock_data(symbol, period=period, interval=interval)
    return history


def fetch_news(symbol: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    yfinance経由でニュースを取得する（簡易版）
    """
    try:
        ticker = yf.Ticker(format_symbol_for_yfinance(symbol))
        items = ticker.news or []
        news_list = []
        for item in items[:limit]:
            # データ構造の正規化
            # 最近のyfinanceは 'content' キー内に詳細を持つ場合がある
            content = item.get("content", item)

            # published日時情報の取得（場所が変動するため複数箇所チェック）
            valid_date = content.get("pubDate") or item.get("providerPublishTime")
            published_at = None

            if valid_date:
                try:
                    if isinstance(valid_date, (int, float)):
                        published_at = datetime.fromtimestamp(valid_date)
                    elif isinstance(valid_date, str):
                        # ISO8601形式の日時文字列をパース（yfinanceのpubDate対応）
                        clean = valid_date.replace("Z", "+00:00")
                        try:
                            published_at = datetime.fromisoformat(clean)
                        except ValueError:
                            # その他の日時フォーマットをフォールバック
                            from dateutil import parser as dateutil_parser

                            published_at = dateutil_parser.parse(valid_date)
                except Exception:
                    published_at = None

            news_list.append(
                {
                    "title": content.get("title", "No Title"),
                    "publisher": (
                        content.get("provider", {}).get("displayName")
                        if isinstance(content.get("provider"), dict)
                        else "Unknown"
                    ),
                    "link": (
                        content.get("canonicalUrl", {}).get("url")
                        if isinstance(content.get("canonicalUrl"), dict)
                        else content.get("link")
                    ),
                    "published_at": published_at,
                    "summary": content.get("summary", ""),
                }
            )
        return news_list
    except Exception as e:
        print(f"ニュース取得エラー: {e}")
        return []


def fetch_dividends(symbol: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    配当履歴を取得する（最新順で最大limit件）
    """
    try:
        ticker = yf.Ticker(format_symbol_for_yfinance(symbol))
        dividends = ticker.dividends
        if dividends is None or dividends.empty:
            return []

        dividends = dividends.sort_index(ascending=False).head(limit)
        records: List[Dict[str, Any]] = []
        for idx, value in dividends.items():
            date_val = idx.to_pydatetime() if hasattr(idx, "to_pydatetime") else idx
            records.append(
                {
                    "date": date_val,
                    "amount": float(value),
                }
            )
        return records
    except Exception as e:
        print(f"配当取得エラー: {e}")
        return []


def fetch_dividend_details(symbol: str) -> Dict[str, Any]:
    """
    配当の詳細情報を取得する。
    j-Quants API を優先し、取得できない場合は yfinance にフォールバックする。

    Returns:
        {
            "source": "jquants" | "yfinance" | "none",
            "records": [  # 配当イベント一覧（日付昇順）
                {"date": datetime, "amount": float, "type": "通常"|"特別"|"不明",
                 "record_date": str|None, "ex_date": str|None, "pay_date": str|None},
            ],
            "ex_dividend_date": str|None,    # 直近の権利落ち日
            "record_date": str|None,         # 直近の権利確定日
            "current_price": float|None,     # 現在株価（利回り計算用）
            "trailing_eps": float|None,      # EPS（配当性向計算用）
        }
    """
    from services.jquants_client import client as jquants_client

    result: Dict[str, Any] = {
        "source": "none",
        "records": [],
        "ex_dividend_date": None,
        "record_date": None,
        "current_price": None,
        "trailing_eps": None,
    }

    # --- 補足情報を yfinance から取得（利回り・配当性向計算用） ---
    try:
        ticker = yf.Ticker(format_symbol_for_yfinance(symbol))
        info = ticker.info or {}
        result["current_price"] = info.get("currentPrice") or info.get(
            "regularMarketPrice"
        )
        result["trailing_eps"] = info.get("trailingEps")
    except Exception as e:
        print(f"yfinance info 取得エラー（配当詳細用）: {e}")

    # --- 1) j-Quants API から配当データ取得 ---
    code_for_jquants = symbol.replace(".T", "") if symbol.endswith(".T") else symbol
    jq_records = []
    try:
        jq_records = jquants_client.get_dividend(code_for_jquants)
    except Exception as e:
        print(f"j-Quants 配当取得エラー: {e}")

    if jq_records:
        result["source"] = "jquants"
        records = []
        for item in jq_records:
            # 配当額
            amount = item.get("DivRate") or item.get("DividendPerShare")
            if amount is None:
                continue
            try:
                amount = float(amount)
            except (ValueError, TypeError):
                continue
            if amount <= 0:
                continue

            # 日付パース
            def _parse_date(val):
                """日付文字列をパースする"""
                if val is None or val == "" or val == "-":
                    return None
                try:
                    return datetime.strptime(
                        str(val).replace("-", "").strip()[:8], "%Y%m%d"
                    )
                except Exception:
                    return None

            rec_date = _parse_date(item.get("RecDate") or item.get("RecordDate"))
            ex_date = _parse_date(item.get("ExDate") or item.get("ExDividendDate"))
            pay_date = _parse_date(item.get("PayStartDate") or item.get("PaymentDate"))
            announce_date = _parse_date(item.get("AnnouncementDate"))

            # 配当種別の判定
            div_type_raw = str(
                item.get("DivType", "") or item.get("DividendType", "")
            ).strip()
            if (
                "特別" in div_type_raw
                or "special" in div_type_raw.lower()
                or "記念" in div_type_raw
            ):
                div_type = "特別"
            elif (
                div_type_raw == ""
                or "中間" in div_type_raw
                or "期末" in div_type_raw
                or "通常" in div_type_raw
            ):
                div_type = "通常"
            else:
                div_type = "通常"

            # 日付の決定（表示用）: rec_date > ex_date > announce_date の優先順
            event_date = rec_date or ex_date or announce_date or pay_date
            if event_date is None:
                continue

            records.append(
                {
                    "date": event_date,
                    "amount": amount,
                    "type": div_type,
                    "record_date": rec_date.strftime("%Y/%m/%d") if rec_date else None,
                    "ex_date": ex_date.strftime("%Y/%m/%d") if ex_date else None,
                    "pay_date": pay_date.strftime("%Y/%m/%d") if pay_date else None,
                }
            )

        # 日付昇順でソート
        records.sort(key=lambda r: r["date"])
        result["records"] = records

        # 直近の権利日を取得
        if records:
            latest = records[-1]
            result["ex_dividend_date"] = latest.get("ex_date")
            result["record_date"] = latest.get("record_date")

    # --- 2) j-Quants が空の場合、yfinance フォールバック ---
    if not result["records"]:
        try:
            ticker = yf.Ticker(format_symbol_for_yfinance(symbol))
            dividends = ticker.dividends
            if dividends is not None and not dividends.empty:
                result["source"] = "yfinance"
                records = []
                for idx, value in dividends.items():
                    date_val = (
                        idx.to_pydatetime() if hasattr(idx, "to_pydatetime") else idx
                    )
                    amt = float(value)
                    if amt <= 0:
                        continue
                    records.append(
                        {
                            "date": date_val,
                            "amount": amt,
                            "type": "不明",  # yfinance では種別不明
                            "record_date": None,
                            "ex_date": None,
                            "pay_date": None,
                        }
                    )
                records.sort(key=lambda r: r["date"])
                result["records"] = records

            # yfinance から権利落ち日を取得
            info = ticker.info or {}
            ex_div_ts = info.get("exDividendDate")
            if ex_div_ts:
                try:
                    if isinstance(ex_div_ts, (int, float)):
                        ex_dt = datetime.fromtimestamp(ex_div_ts)
                    else:
                        ex_dt = datetime.strptime(str(ex_div_ts), "%Y-%m-%d")
                    result["ex_dividend_date"] = ex_dt.strftime("%Y/%m/%d")
                except Exception:
                    pass
        except Exception as e:
            print(f"yfinance 配当フォールバックエラー: {e}")

    return result
