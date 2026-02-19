
import os
import requests
import logging
import time
from datetime import datetime, timedelta

from typing import Optional, Dict, List, Any
from dotenv import load_dotenv

# Load env vars from .env file if present
load_dotenv()

logger = logging.getLogger(__name__)

class JQuantsClient:
    BASE_URL = "https://api.jquants.com/v2"
    
    def __init__(self):
        self.api_key = os.environ.get("JQUANTS_API_KEY")
        
        if not self.api_key:
             logger.warning("JQUANTS_API_KEY not set. J-Quants features will be unavailable.")

    def get(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        V2 API 用の認証済み GET リクエスト。
        x-api-key ヘッダーで認証する。
        """
        if not self.api_key:
            return {}
            
        url = f"{self.BASE_URL}{endpoint}"
        headers = {"x-api-key": self.api_key}
        
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=20)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            # Free プラン制限 (403) はwarningレベルでログ出力
            if e.response is not None and e.response.status_code == 403:
                logger.warning(f"J-Quants API 403 Forbidden ({endpoint}): Free プランでは利用不可")
            else:
                logger.error(f"J-Quants API Request Failed ({endpoint}): {e}")
            return {}
        except Exception as e:
            logger.error(f"J-Quants API Request Failed ({endpoint}): {e}")
            return {}

    def get_all(self, endpoint: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        ページネーション対応の全件取得。
        V2 API は "pagination_key" でページ分割する。
        """
        all_data: List[Dict[str, Any]] = []
        current_params = dict(params) if params else {}

        while True:
            resp = self.get(endpoint, current_params)
            if not resp:
                break
            data = resp.get("data", [])
            all_data.extend(data)

            # 次ページがあれば継続
            pagination_key = resp.get("pagination_key")
            if pagination_key:
                current_params["pagination_key"] = pagination_key
                time.sleep(0.5)  # レートリミット対策
            else:
                break

        return all_data

    def get_daily_quotes(self, code: str, date: str = None, from_date: str = None, to_date: str = None) -> Dict[str, Any]:
        """
        /equities/bars/daily
        """
        params = {"code": code}
        if date:
            params["date"] = date.replace("-", "") # J-Quants uses YYYYMMDD
        if from_date:
            params["from"] = from_date.replace("-", "")
        if to_date:
            params["to"] = to_date.replace("-", "")
            
        resp = self.get("/equities/bars/daily", params)
        
        if "data" in resp:
            # Map keys O->Open, H->High, etc.
            standardized = []
            for item in resp["data"]:
                new_item = item.copy()
                mapping = {
                    "O": "Open", "H": "High", "L": "Low", "C": "Close", "Vo": "Volume",
                    "AdjO": "AdjOpen", "AdjH": "AdjHigh", "AdjL": "AdjLow", "AdjC": "AdjClose", "AdjVo": "AdjVolume"
                }
                for old_k, new_k in mapping.items():
                    if old_k in new_item:
                         new_item[new_k] = new_item.pop(old_k)
                standardized.append(new_item)
            
            resp["daily_quotes"] = standardized
            
        return resp

    def get_dividend(self, code: str) -> List[Dict[str, Any]]:
        """
        /fins/dividend エンドポイントから配当情報を取得する。
        ※ Free プランでは 403 エラー（Light 以上が必要）

        Returns:
            配当レコードのリスト。V2 レスポンスの "data" キーから取得。
            取得失敗時は空リストを返す。
        """
        if not self.api_key:
            return []
        # V2 API は5桁コードを要求する場合がある
        code = self._normalize_code(code)
        params = {"code": code}
        resp = self.get("/fins/dividend", params)
        # V2 レスポンス: {"data": [...]} を優先
        if isinstance(resp, dict):
            return resp.get("data", [])
        return []

    def get_listed_info(self, code: str = None, date: str = None) -> Dict[str, Any]:
        """
        /equities/master から銘柄情報を取得する。
        code を指定すると単一銘柄、未指定で全銘柄を返す。

        Returns:
            V2 レスポンス: {"data": [{...}, ...]} 形式
        """
        if not self.api_key:
            return {}
        params = {}
        if code:
            params["code"] = self._normalize_code(code)
        if date:
            params["date"] = date.replace("-", "")
        else:
            # Free プラン対応: 12週前の日付を使用
            target_date = datetime.now() - timedelta(weeks=13)
            params["date"] = target_date.strftime("%Y%m%d")

        resp = self.get("/equities/master", params)
        return resp

    def get_financial_summary(self, code: str) -> List[Dict[str, Any]]:
        """
        /fins/summary から財務サマリーを取得する。
        Free プランでも利用可能。

        Returns:
            財務サマリーレコードのリスト。
        """
        if not self.api_key:
            return []
        code = self._normalize_code(code)
        return self.get_all("/fins/summary", {"code": code})

    @staticmethod
    def _normalize_code(code: str) -> str:
        """
        銘柄コードを J-Quants V2 用に正規化する。
        4桁コード → 5桁（末尾0付加）、.T サフィックス除去。
        """
        code = code.replace(".T", "").strip()
        # 4桁の場合は5桁に拡張（J-Quants V2は5桁コードを使用）
        if len(code) == 4 and code.isdigit():
            code = code + "0"
        return code

    def get_listed_issues(self) -> List[Dict[str, Any]]:
        """
        上場銘柄一覧を取得する（/equities/master）。
        Free プランの日付制限に対応したフォールバック戦略:
        1. 当日（Premium/Standard）
        2. 13週前（Free プラン対応）
        3. 直近7日間（祝日・週末対応）
        4. 固定日付フォールバック
        """
        strategies = [
            # (説明, 日付)
            ("today", datetime.now().strftime("%Y%m%d")),
            ("13w_ago", (datetime.now() - timedelta(weeks=13)).strftime("%Y%m%d")),
        ]
        # 直近7日間を追加
        for i in range(1, 8):
            d = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
            strategies.append((f"day_minus_{i}", d))
        # 固定日付フォールバック
        strategies.append(("deep_fallback", "20240104"))

        for label, date_str in strategies:
            try:
                resp = self.get("/equities/master", {"date": date_str})
                if isinstance(resp, dict) and "data" in resp and resp["data"]:
                    logger.info(f"J-Quants: マスターデータ取得成功 date={date_str} ({label})")
                    return resp["data"]
            except Exception:
                pass
            time.sleep(0.5)  # レートリミット対策（Free: 5req/min）

        logger.error("J-Quants: マスターデータを取得できませんでした")
        return []

    def get_margin_interest(self, code: str) -> List[Dict[str, Any]]:
        """
        /markets/margin-interest から信用取引週末残高を取得する。
        前週比の算出に必要な直近データを返す。
        Free プランでは取得制限の可能性あり。

        Returns:
            信用残レコードのリスト（日付降順）。
            取得失敗時は空リストを返す。
        """
        if not self.api_key:
            return []
        code = self._normalize_code(code)
        # 直近の信用残データを取得（前週比計算のため複数件）
        resp = self.get("/markets/margin-interest", {"code": code})
        if isinstance(resp, dict):
            data = resp.get("data", [])
            # 日付降順にソート（最新が先頭）
            data.sort(key=lambda x: x.get("Date", ""), reverse=True)
            return data
        return []

# Global instance
client = JQuantsClient()
