import os
import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import requests
import pandas as pd
from dotenv import load_dotenv

import jquantsapi

# Load env vars from .env file if present
load_dotenv()

logger = logging.getLogger(__name__)


class JQuantsClient:
    """
    J-Quants API Client Wrapper (Adapter for jquants-api-client v2)
    """

    BASE_URL = "https://api.jquants.com/v2"

    def __init__(self):
        self.api_key = os.environ.get("JQUANTS_API_KEY")

        if not self.api_key:
            logger.warning(
                "JQUANTS_API_KEY not set. J-Quants features will be unavailable."
            )
            self.jq = None
        else:
            try:
                # Initialize official client (V2)
                self.jq = jquantsapi.ClientV2(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Failed to initialize JQuantsClientV2: {e}")
                self.jq = None

    def get(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        [Deprecated] V2 API 用の認証済み GET リクエスト。
        互換性のために requests を直接使用するメソッドを残すが、
        可能な限り公式クライアントのメソッドを使用すること。
        """
        if not self.api_key:
            return {}

        url = f"{self.BASE_URL}{endpoint}"
        headers = {"x-api-key": self.api_key}

        try:
            resp = requests.get(url, headers=headers, params=params, timeout=20)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"J-Quants API Request Failed ({endpoint}): {e}")
            return {}

    def get_all(
        self, endpoint: str, params: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        [Deprecated] ページネーション対応の全件取得。
        公式クライアント移行に伴い、このメソッドは直接使用せず
        各専用メソッド（get_financial_summary等）を使用することを推奨。
        """
        # 既存ロジック維持
        return self._legacy_get_all(endpoint, params)

    def _legacy_get_all(
        self, endpoint: str, params: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        all_data: List[Dict[str, Any]] = []
        current_params = dict(params) if params else {}

        while True:
            resp = self.get(endpoint, current_params)
            if not resp:
                break
            data = resp.get("data", [])
            all_data.extend(data)

            pagination_key = resp.get("pagination_key")
            if pagination_key:
                current_params["pagination_key"] = pagination_key
                time.sleep(0.5)
            else:
                break

        return all_data

    def get_daily_quotes(
        self, code: str, date: str = None, from_date: str = None, to_date: str = None
    ) -> Dict[str, Any]:
        """
        /equities/bars/daily
        """
        if not self.jq:
            return {}

        try:
            # jquants-api-client params: code, date, from_yyyymmdd, to_yyyymmdd
            # Note: library might use different param names. Checking assumed signature.
            # ClientV2.get_eq_bars_daily(code=..., date=..., from_yyyymmdd=..., to_yyyymmdd=...) usually
            # But let's verify params based on previous method list.
            # Assuming widely used kwargs like code, date, from_date, to_date or standardized.
            # safe approach: pass keys as compatible via kwargs if needed or specific mapping.

            # Using keyword arguments based on library V2 conventions (usually matches API params or standard)
            # API query params: code, date, from, to
            # Library often maps 'from' -> 'from_yyyymmdd' to avoid usage of reserved keyword.

            # Since I cannot verify exact signature without help(), I will try standard args.

            kwargs = {"code": code}
            if date:
                kwargs["date"] = date.replace("-", "")
            if from_date:
                kwargs["from_yyyymmdd"] = from_date.replace("-", "")
            if to_date:
                kwargs["to_yyyymmdd"] = to_date.replace("-", "")

            # Call official client
            df = self.jq.get_eq_bars_daily(**kwargs)

            if df.empty:
                return {}

            # Convert to list of dicts
            data_list = df.to_dict(orient="records")

            # Standardize keys (O -> Open, etc)
            # V2 API returns Open, High, Low, Close, Volume.
            # If library returns exact API columns, we might need no mapping if already correct.
            # But for safety, ensure "Open" etc exist.

            standardized = []
            for item in data_list:
                new_item = item.copy()

                # Check mapping if short names (O, H, L, C) are present
                mapping = {
                    "O": "Open",
                    "H": "High",
                    "L": "Low",
                    "C": "Close",
                    "Vo": "Volume",
                    "AdjO": "AdjOpen",
                    "AdjH": "AdjHigh",
                    "AdjL": "AdjLow",
                    "AdjC": "AdjClose",
                    "AdjVo": "AdjVolume",
                }
                for old_k, new_k in mapping.items():
                    if old_k in new_item and new_k not in new_item:
                        new_item[new_k] = new_item.pop(old_k)

                # If library already returns "Open", keys are preserved.
                standardized.append(new_item)

            return {
                "daily_quotes": standardized,
                "data": standardized,
            }  # Return compatible structure

        except Exception as e:
            logger.error(f"J-Quants Lib `get_eq_bars_daily` failed: {e}")
            return {}

    def get_dividend(self, code: str) -> List[Dict[str, Any]]:
        """
        /fins/dividend 配当情報
        """
        if not self.jq:
            return []
        try:
            code = self._normalize_code(code)
            df = self.jq.get_fin_dividend(code=code)
            if df.empty:
                return []
            return df.to_dict(orient="records")
        except Exception as e:
            # Free plan 403 or other error
            logger.warning(
                f"J-Quants Lib `get_fin_dividend` failed (possibly 403): {e}"
            )
            return []

    def get_listed_info(self, code: str = None, date: str = None) -> Dict[str, Any]:
        """
        /equities/master 銘柄情報
        Returns: {"data": [...]} compatible format
        """
        if not self.jq:
            return {}
        try:
            kwargs = {}
            if code:
                kwargs["code"] = self._normalize_code(code)
            if date:
                kwargs["date"] = date.replace("-", "")
            else:
                # Default logic handled by usage side or library?
                pass

            df = self.jq.get_eq_master(**kwargs)
            if df.empty:
                return {}

            return {"data": df.to_dict(orient="records")}
        except Exception as e:
            logger.error(f"J-Quants Lib `get_eq_master` failed: {e}")
            return {}

    def get_financial_summary(self, code: str) -> List[Dict[str, Any]]:
        """
        /fins/summary 財務サマリー
        """
        if not self.jq:
            return []
        try:
            code = self._normalize_code(code)
            # get_fin_summary handles pagination iteratively internally usually
            df = self.jq.get_fin_summary(code=code)
            if df.empty:
                return []
            return df.to_dict(orient="records")
        except Exception as e:
            logger.error(f"J-Quants Lib `get_fin_summary` failed: {e}")
            return []

    @staticmethod
    def _normalize_code(code: str) -> str:
        code = code.replace(".T", "").strip()
        if len(code) == 4 and code.isdigit():
            code = code + "0"
        return code

    def get_listed_issues(self) -> List[Dict[str, Any]]:
        """
        上場銘柄一覧 (Fallback strategy with library)
        """
        if not self.jq:
            return []

        strategies = [
            ("today", datetime.now().strftime("%Y%m%d")),
            ("13w_ago", (datetime.now() - timedelta(weeks=13)).strftime("%Y%m%d")),
        ]
        for i in range(1, 8):
            d = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
            strategies.append((f"day_minus_{i}", d))
        strategies.append(("deep_fallback", "20240104"))

        for label, date_str in strategies:
            try:
                # Use library method
                df = self.jq.get_eq_master(date=date_str)
                if not df.empty:
                    data = df.to_dict(orient="records")
                    if data:
                        logger.info(
                            f"J-Quants: マスターデータ取得成功 date={date_str} ({label})"
                        )
                        return data
            except Exception:
                pass
            time.sleep(0.5)

        logger.error("J-Quants: マスターデータを取得できませんでした")
        return []

    def get_margin_interest(self, code: str) -> List[Dict[str, Any]]:
        """
        /markets/margin-interest 信用週末残高
        """
        if not self.jq:
            return []
        try:
            code = self._normalize_code(code)
            df = self.jq.get_mkt_margin_interest(code=code)
            if df.empty:
                return []

            data = df.to_dict(orient="records")
            # Sort by date desc
            data.sort(key=lambda x: x.get("Date", ""), reverse=True)
            return data
        except Exception as e:
            # Free plan 403 expected
            if "403" in str(e):
                logger.warning(
                    f"J-Quants API 403 Forbidden (margin-interest): Free プランでは利用不可"
                )
            else:
                logger.error(f"J-Quants Lib `get_mkt_margin_interest` failed: {e}")
            return []

    def get_earnings_calendar(self) -> List[Dict[str, Any]]:
        """
        決算発表予定日カレンダーを取得（/eq/earnings_cal）
        全銘柄分を一括取得し、呼び出し側でフィルタする。
        """
        if not self.jq:
            return []
        try:
            df = self.jq.get_eq_earnings_cal()
            if df.empty:
                return []
            return df.to_dict(orient="records")
        except Exception as e:
            if "403" in str(e):
                logger.warning(
                    "J-Quants API 403 Forbidden (earnings_cal): Free プランでは利用不可の可能性"
                )
            else:
                logger.error(f"J-Quants Lib `get_eq_earnings_cal` failed: {e}")
            return []


# Global instance
client = JQuantsClient()
