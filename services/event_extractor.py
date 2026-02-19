"""
2段階イベント抽出ロジック

ステップ1: キーワードマッチでevent_type仮決定（ルールベース）
ステップ2: 否定語チェック＋文脈確認で確度調整

仕様書§4準拠のevent_type / impact_type / impact_strength マッピング。
"""

import unicodedata
import re
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


# ============================================================
# イベントタイプ定義（仕様書§4準拠）
# ============================================================

# キーワード → event_type マッピング
# 複数キーワードのOR検索、優先度は上から順
EVENT_KEYWORD_RULES: List[Dict[str, Any]] = [
    {
        "event_type": "TOB",
        "keywords": ["公開買付", "公開買い付け", "TOB", "株式公開買付"],
        "description": "公開買付け（TOB）",
    },
    {
        "event_type": "BUYBACK",
        "keywords": ["自己株式取得", "自社株買い", "自己株式の取得", "自己株式の消却"],
        "description": "自社株買い",
    },
    {
        "event_type": "DELISTING",
        "keywords": ["上場廃止", "上場の廃止"],
        "description": "上場廃止",
    },
    {
        "event_type": "UPWARD_REVISION",
        "keywords": ["上方修正", "業績予想の修正.*上方", "通期業績予想.*上方"],
        "description": "上方修正",
    },
    {
        "event_type": "DOWNWARD_REVISION",
        "keywords": ["下方修正", "業績予想の修正.*下方", "通期業績予想.*下方"],
        "description": "下方修正",
    },
    {
        "event_type": "DIVIDEND_UP",
        "keywords": ["増配", "配当.*増額", "配当金の増額"],
        "description": "増配",
    },
    {
        "event_type": "DIVIDEND_DOWN",
        "keywords": ["減配", "配当.*減額", "無配", "配当金の減額"],
        "description": "減配",
    },
    {
        "event_type": "IMPAIRMENT",
        "keywords": ["減損", "減損損失", "特別損失.*減損"],
        "description": "減損損失",
    },
]

# event_type → impact_type 初期マッピング（仕様書§4）
IMPACT_TYPE_MAP: Dict[str, str] = {
    "TOB": "POSITIVE",
    "BUYBACK": "POSITIVE",
    "DELISTING": "NEGATIVE",
    "UPWARD_REVISION": "POSITIVE",
    "DOWNWARD_REVISION": "NEGATIVE",
    "DIVIDEND_UP": "POSITIVE",
    "DIVIDEND_DOWN": "NEGATIVE",
    "IMPAIRMENT": "NEGATIVE",
}

# event_type → impact_strength 初期マッピング（仕様書§4）
# 原則MEDIUM、明確重大事象のみHIGH
IMPACT_STRENGTH_MAP: Dict[str, str] = {
    "TOB": "HIGH",
    "BUYBACK": "MEDIUM",
    "DELISTING": "HIGH",
    "UPWARD_REVISION": "MEDIUM",
    "DOWNWARD_REVISION": "MEDIUM",
    "DIVIDEND_UP": "LOW",
    "DIVIDEND_DOWN": "LOW",
    "IMPAIRMENT": "MEDIUM",
}

# 否定語リスト（ステップ2で使用）
NEGATION_KEYWORDS = [
    "中止", "撤回", "延期", "見送り", "取り消し", "取消",
    "断念", "白紙", "凍結", "解消",
]


def normalize_text(text: str) -> str:
    """NFKC正規化＋小文字化"""
    if not text:
        return ""
    return unicodedata.normalize("NFKC", text).strip()


class EventExtractor:
    """2段階イベント抽出ロジック"""

    def extract_events(self, document: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        EDINETドキュメントメタデータからイベントを抽出する。

        Args:
            document: EDINETのdocuments.json結果の1件分
                必須キー: docID, secCode, filerName, docDescription

        Returns:
            抽出されたイベントのリスト（0件の場合あり）
        """
        doc_id = document.get("docID", "")
        sec_code = document.get("secCode", "")
        filer_name = document.get("filerName", "")
        doc_description = document.get("docDescription", "")
        submit_datetime = document.get("submitDateTime", "")

        # sec_codeがない場合はスキップ（企業以外の提出者）
        if not sec_code or sec_code.strip() == "":
            return []

        # sec_codeを5桁に正規化（末尾の0を含む）
        sec_code = sec_code.strip()[:5]

        # タイトルテキストを構築（NFKC正規化）
        title_text = normalize_text(f"{filer_name} {doc_description}")

        # ステップ1: キーワードマッチ
        candidates = self._step1_keyword_match(title_text)

        if not candidates:
            return []

        # ステップ2: 文脈確認（各候補に対して）
        results = []
        for event_type, matched_keyword in candidates:
            impact_type, impact_strength, extraction_method = self._step2_context_check(
                title_text, event_type
            )

            # announced_at をパース
            announced_at = self._parse_datetime(submit_datetime)

            results.append({
                "doc_id": doc_id,
                "sec_code": sec_code,
                "event_type": event_type,
                "title": normalize_text(doc_description) or normalize_text(filer_name),
                "source_name": "EDINET_API",
                "extraction_method": extraction_method,
                "announced_at": announced_at,
                "impact_type": impact_type,
                "impact_strength": impact_strength,
                "matched_keyword": matched_keyword,
                "summary_2lines": self._build_summary(filer_name, doc_description, event_type),
            })

        return results

    def _step1_keyword_match(self, text: str) -> List[Tuple[str, str]]:
        """
        ステップ1: キーワードマッチでevent_type候補を抽出。

        Returns:
            (event_type, matched_keyword) のリスト
        """
        matches = []
        for rule in EVENT_KEYWORD_RULES:
            for kw in rule["keywords"]:
                # 正規表現対応（.*を含むキーワード）
                if ".*" in kw or "*" in kw:
                    if re.search(kw, text):
                        matches.append((rule["event_type"], kw))
                        break
                else:
                    if kw in text:
                        matches.append((rule["event_type"], kw))
                        break

        return matches

    def _step2_context_check(
        self, text: str, event_type: str
    ) -> Tuple[str, str, str]:
        """
        ステップ2: 文脈確認。否定語チェックで確度調整。

        Returns:
            (impact_type, impact_strength, extraction_method)
        """
        # 否定語チェック
        has_negation = any(neg in text for neg in NEGATION_KEYWORDS)

        if has_negation:
            # 否定語を含む場合
            logger.info(f"否定語検出: event_type={event_type}, text={text[:80]}")

            # TOBの撤回はNEGATIVEに反転
            if event_type == "TOB":
                return "NEGATIVE", "MEDIUM", "CONTEXT"

            # その他は不確実 → NEUTRAL
            return "NEUTRAL", "LOW", "CONTEXT"

        # 否定語なし → ルール通りのimpact判定
        impact_type = IMPACT_TYPE_MAP.get(event_type, "NEUTRAL")
        impact_strength = IMPACT_STRENGTH_MAP.get(event_type, "LOW")

        return impact_type, impact_strength, "RULE"

    def _parse_datetime(self, dt_str: str) -> Optional[datetime]:
        """EDINET日時文字列をパース"""
        if not dt_str:
            return None

        # EDINETのsubmitDateTime形式: "2024-01-15 09:00"
        formats = [
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(dt_str.strip(), fmt)
            except ValueError:
                continue

        logger.warning(f"日時パース失敗: {dt_str}")
        return None

    def _build_summary(self, filer_name: str, doc_description: str, event_type: str) -> str:
        """2行サマリーを構築"""
        # イベントタイプの日本語ラベル
        type_labels = {
            "TOB": "公開買付け",
            "BUYBACK": "自社株買い",
            "DELISTING": "上場廃止",
            "UPWARD_REVISION": "上方修正",
            "DOWNWARD_REVISION": "下方修正",
            "DIVIDEND_UP": "増配",
            "DIVIDEND_DOWN": "減配",
            "IMPAIRMENT": "減損損失",
        }
        label = type_labels.get(event_type, event_type)
        filer = normalize_text(filer_name)
        desc = normalize_text(doc_description)

        line1 = f"{filer}: {label}"
        line2 = desc[:100] if desc else ""

        return f"{line1}\n{line2}".strip()
