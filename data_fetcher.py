"""
株価データ取得モジュール
外部API（yfinance）から株価データや情報を取得する
"""

from datetime import datetime
from typing import Optional, Dict, Any, List

import pandas as pd
import yfinance as yf


def fetch_stock_data(symbol: str, period: str = "1mo",
                     interval: str = "1d") -> Optional[pd.DataFrame]:
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
            "market_cap": info.get("marketCap"),
            "currency": info.get("currency", "JPY"),
            "exchange": info.get("exchange", ""),
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
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
    symbol: str,
    periods: Optional[Dict[str, tuple[str, str]]] = None
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
            published = item.get("providerPublishTime")
            published_at = None
            if isinstance(published, (int, float)):
                try:
                    published_at = datetime.fromtimestamp(published)
                except Exception:
                    published_at = None

            news_list.append({
                "title": item.get("title"),
                "publisher": item.get("publisher"),
                "link": item.get("link"),
                "published_at": published_at,
                "summary": item.get("summary"),
            })
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
            records.append({
                "date": date_val,
                "amount": float(value),
            })
        return records
    except Exception as e:
        print(f"配当取得エラー: {e}")
        return []
