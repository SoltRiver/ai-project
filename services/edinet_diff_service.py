"""
EDINET 差分比較サービス

有価証券報告書（年次）の前回/今回比較を行い、
固定6指標の差分テーブルと変化が大きい上位3項目を生成する。

投資助言/推奨は一切含めない。
差分は事実（今回/前回/差分/差分率）と根拠に徹する。
"""

import logging
import yaml
import os
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional, Dict, Any, List, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import desc

from database import SessionLocal
from models.edinet_document import EdinetDocument
from models.edinet_financial_highlight import EdinetFinancialHighlight
from models.edinet_facts_snapshot import EdinetFactsSnapshot
from models.edinet_diff_summary import EdinetDiffSummary

logger = logging.getLogger(__name__)

# ==============================================================
# 定数
# ==============================================================

# 固定6項目のキー（表示順）
FIXED_SIX_KEYS = [
    "revenue",
    "operating_profit",
    "net_income",
    "operating_cf",
    "total_assets",
    "equity_ratio",
]

# 有価証券報告書（年次）の doc_type_code
ANNUAL_DOC_TYPE = "120"

# 単位変換マップ（すべて JPY に正規化）
UNIT_CONVERSION = {
    "JPY": Decimal("1"),
    "jpy": Decimal("1"),
    "円": Decimal("1"),
    "thousand_JPY": Decimal("1000"),
    "千円": Decimal("1000"),
    "million_JPY": Decimal("1000000"),
    "百万円": Decimal("1000000"),
}

# カテゴリ優先順（タイブレーク用）: PL > CF > BS
CATEGORY_PRIORITY = {"PL": 0, "CF": 1, "BS": 2}

# 閾値定数
THRESHOLD_A_RATIO = Decimal("0.005")      # 相対条件: 0.5%
THRESHOLD_B_PREV_MIN = Decimal("0.01")    # prev安定化条件: 1%
THRESHOLD_B_PCT = Decimal("0.10")         # 率条件: 10%
PCT_CLIP_MAX = Decimal("3.0")             # pct_part 上限 300%

# metric_key → EdinetFinancialHighlight の metric_key マッピング
# EdinetFinancialHighlight は net_sales, operating_income 等の名称を使う場合がある
HIGHLIGHT_KEY_MAP = {
    "revenue": ["net_sales", "revenue", "operating_revenue"],
    "operating_profit": ["operating_profit", "operating_income"],
    "net_income": ["net_income", "net_profit", "profit_loss"],
    "operating_cf": ["operating_cf", "cash_flows_operating", "net_cash_operating"],
    "total_assets": ["total_assets"],
    "equity": ["equity", "shareholders_equity", "net_assets"],
    "ordinary_profit": ["ordinary_profit", "ordinary_income"],
    "investing_cf": ["investing_cf", "cash_flows_investing", "net_cash_investing"],
    "financing_cf": ["financing_cf", "cash_flows_financing", "net_cash_financing"],
    "cash_end": ["cash_end", "cash_and_equivalents", "cash_and_cash_equivalents"],
    "net_assets": ["net_assets"],
}


def _load_metrics_config() -> List[Dict[str, Any]]:
    """edinet_metrics.yml を読み込む"""
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "edinet_metrics.yml")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("metrics", [])
    except Exception as e:
        logger.error(f"metrics設定ファイルの読み込み失敗: {e}")
        return []


def _get_metric_config(metric_key: str) -> Optional[Dict[str, Any]]:
    """指定 metric_key の設定を取得"""
    for m in _load_metrics_config():
        if m["metric_key"] == metric_key:
            return m
    return None


# ==============================================================
# 単位正規化
# ==============================================================

def normalize_unit(value: Any, unit: Optional[str]) -> Tuple[Optional[Decimal], str]:
    """
    値と単位を受け取り、JPY基準に正規化する。
    
    Returns:
        (normalized_value, "JPY") or (None, "unknown") — 変換不能の場合
    """
    if value is None:
        return None, "unknown"

    try:
        dec_value = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None, "unknown"

    if unit is None or unit.strip() == "":
        # 単位が無い場合でも数値がある場合はそのまま使用（JPY仮定）
        return dec_value, "JPY"

    unit_clean = unit.strip()
    factor = UNIT_CONVERSION.get(unit_clean)

    if factor is not None:
        return dec_value * factor, "JPY"
    
    # 変換不能な単位
    logger.warning(f"変換不能な単位: {unit_clean}（欠損扱い）")
    return None, "unknown"


# ==============================================================
# prev 決定ロジック
# ==============================================================

def find_prev_doc(
    db: Session,
    current_doc: EdinetDocument,
    current_scope: Optional[str] = None
) -> Optional[EdinetDocument]:
    """
    prev（前回比較対象）を決定する。

    ルール:
    1) 同一 stock_code（sec_code）
    2) 同一 doc_type（年次 = 120）
    3) is_correction = false（v1では訂正は除外するが、既存DBにカラムがない場合はスキップ）
    4) submit_date が current より過去のうち最も新しい1件
    5) consolidation_scope が一致する候補を優先
    """
    if not current_doc.sec_code:
        logger.warning(f"sec_code が無い書類: {current_doc.doc_id}")
        return None

    # 基本クエリ: 同一 sec_code + 年次報告書 + submit_datetime が過去
    query = db.query(EdinetDocument).filter(
        EdinetDocument.sec_code == current_doc.sec_code,
        EdinetDocument.doc_type_code == ANNUAL_DOC_TYPE,
        EdinetDocument.doc_id != current_doc.doc_id,
    )

    # submit_datetime が current より過去
    if current_doc.submit_datetime:
        query = query.filter(
            EdinetDocument.submit_datetime < current_doc.submit_datetime
        )
    elif current_doc.target_date:
        query = query.filter(
            EdinetDocument.target_date < current_doc.target_date
        )

    # submit_datetime 降順で候補を取得（最大5件で十分）
    candidates = query.order_by(
        desc(EdinetDocument.submit_datetime)
    ).limit(5).all()

    if not candidates:
        return None

    # consolidation_scope が一致する候補を優先
    if current_scope:
        for cand in candidates:
            # 候補の scope を facts_snapshot から取得
            cand_scope = _get_doc_scope(db, cand.doc_id)
            if cand_scope == current_scope:
                return cand

    # scope 一致なしまたは scope 不明の場合は最新の候補を返す
    return candidates[0]


def _get_doc_scope(db: Session, doc_id: str) -> Optional[str]:
    """指定書類の consolidation_scope を取得（facts_snapshot から）"""
    fact = db.query(EdinetFactsSnapshot).filter(
        EdinetFactsSnapshot.doc_id == doc_id,
        EdinetFactsSnapshot.consolidation_scope.isnot(None),
        EdinetFactsSnapshot.consolidation_scope != "unknown",
    ).first()
    return fact.consolidation_scope if fact else None


# ==============================================================
# ファクトスナップショット構築
# ==============================================================

def build_facts_snapshot(db: Session, doc_id: str) -> Dict[str, Dict[str, Any]]:
    """
    EdinetFinancialHighlight からデータを読み取り、
    edinet_facts_snapshot テーブルに正規化して保存する。
    
    Returns:
        metric_key → {value, unit, consolidation_scope, source_locator} の辞書
    """
    # 既存の snapshot があれば返す
    existing = db.query(EdinetFactsSnapshot).filter(
        EdinetFactsSnapshot.doc_id == doc_id
    ).all()
    
    if existing:
        result = {}
        for snap in existing:
            result[snap.metric_key] = {
                "value": snap.value,
                "unit": snap.unit,
                "consolidation_scope": snap.consolidation_scope,
                "source_locator": snap.source_locator,
            }
        return result

    # EdinetFinancialHighlight から取得
    highlights = db.query(EdinetFinancialHighlight).filter(
        EdinetFinancialHighlight.doc_id == doc_id
    ).all()

    if not highlights:
        logger.warning(f"doc_id={doc_id} の FinancialHighlight データなし")
        return {}

    # highlight の metric_key → 値のマップを作成
    hl_map: Dict[str, EdinetFinancialHighlight] = {}
    for hl in highlights:
        hl_map[hl.metric_key] = hl

    # sec_code を取得
    doc = db.query(EdinetDocument).filter(EdinetDocument.doc_id == doc_id).first()
    stock_code = doc.sec_code if doc else None

    result = {}

    # 全 metric_key について変換
    for our_key, hl_keys in HIGHLIGHT_KEY_MAP.items():
        hl = None
        for hk in hl_keys:
            if hk in hl_map:
                hl = hl_map[hk]
                break
        
        if hl is None:
            continue

        # 単位正規化
        norm_value, norm_unit = normalize_unit(hl.value_numeric, hl.unit_label)

        # スコープ判定
        scope = hl.scope if hl.scope else "unknown"

        # DB に保存
        snapshot = EdinetFactsSnapshot(
            doc_id=doc_id,
            stock_code=stock_code,
            metric_key=our_key,
            value=norm_value,
            unit=norm_unit,
            consolidation_scope=scope,
            source_locator=hl.source_concept,
        )
        db.add(snapshot)

        result[our_key] = {
            "value": norm_value,
            "unit": norm_unit,
            "consolidation_scope": scope,
            "source_locator": hl.source_concept,
        }

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"facts_snapshot 保存失敗: {e}")

    return result


# ==============================================================
# 差分計算
# ==============================================================

def _compute_metric_diff(
    current_val: Optional[Decimal],
    prev_val: Optional[Decimal],
    metric_key: str,
) -> Dict[str, Any]:
    """
    個別指標の差分を計算する。
    
    Returns:
        {current_value, prev_value, delta, delta_pct, is_missing}
    """
    # current 側が欠損 → is_missing
    if current_val is None:
        return {
            "current_value": None,
            "prev_value": str(prev_val) if prev_val is not None else None,
            "delta": None,
            "delta_pct": None,
            "is_missing": True,
        }

    # prev 側のみ欠損（初回取得 or 前回値なし）→ 今回値は表示可
    if prev_val is None:
        return {
            "current_value": str(current_val),
            "prev_value": None,
            "delta": None,
            "delta_pct": None,
            "is_missing": False,
        }

    delta = current_val - prev_val
    
    # delta_pct: prev_value が 0 の場合は null
    delta_pct = None
    if prev_val != 0:
        delta_pct = float(delta / prev_val)

    return {
        "current_value": str(current_val),
        "prev_value": str(prev_val),
        "delta": str(delta),
        "delta_pct": delta_pct,
        "is_missing": False,
    }


def compute_fixed_six(
    current_facts: Dict[str, Dict[str, Any]],
    prev_facts: Optional[Dict[str, Dict[str, Any]]],
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    固定6項目の差分を計算する。

    equity_ratio は equity / total_assets で算出する。
    equity が欠損の場合は固定 notes を追加する。
    
    Returns:
        (fixed_six_list, notes_list)
    """
    notes = []
    results = []

    # equity_ratio を先に算出して current/prev に追加
    _compute_equity_ratio(current_facts, notes, "今回")
    if prev_facts:
        _compute_equity_ratio(prev_facts, notes, "前回")

    for key in FIXED_SIX_KEYS:
        config = _get_metric_config(key)
        label = config["metric_label"] if config else key

        current_data = current_facts.get(key, {})
        current_val = current_data.get("value")

        prev_val = None
        if prev_facts:
            prev_data = prev_facts.get(key, {})
            prev_val = prev_data.get("value")

        diff = _compute_metric_diff(current_val, prev_val, key)

        results.append({
            "metric_key": key,
            "metric_label": label,
            "current_value": diff["current_value"],
            "prev_value": diff["prev_value"],
            "delta": diff["delta"],
            "delta_pct": diff["delta_pct"],
            "is_missing": diff["is_missing"],
            "unit": current_data.get("unit", "—"),
            "consolidation_scope": current_data.get("consolidation_scope", "—"),
            "source_locator": current_data.get("source_locator", "—"),
        })

    return results, notes


def _compute_equity_ratio(
    facts: Dict[str, Dict[str, Any]],
    notes: List[str],
    label: str,
) -> None:
    """equity_ratio = equity / total_assets を算出して facts に追加"""
    equity_data = facts.get("equity", {})
    total_assets_data = facts.get("total_assets", {})

    equity_val = equity_data.get("value")
    total_assets_val = total_assets_data.get("value")

    if equity_val is None:
        notes.append("自己資本が未取得のため算出不可")
        return

    if total_assets_val is None or total_assets_val == 0:
        notes.append(f"{label}の総資産が未取得または0のため自己資本比率算出不可")
        return

    try:
        ratio = Decimal(str(equity_val)) / Decimal(str(total_assets_val))
        facts["equity_ratio"] = {
            "value": ratio,
            "unit": "ratio",
            "consolidation_scope": equity_data.get("consolidation_scope", "unknown"),
            "source_locator": f"equity({equity_data.get('source_locator', '—')}) / total_assets({total_assets_data.get('source_locator', '—')})",
        }
    except Exception as e:
        notes.append(f"自己資本比率の算出に失敗: {e}")


# ==============================================================
# 変化大3件の抽出
# ==============================================================

def extract_top_changes(
    current_facts: Dict[str, Dict[str, Any]],
    prev_facts: Dict[str, Dict[str, Any]],
    fixed_keys: List[str],
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    変化が大きい項目を最大3件抽出する。

    抽出手順:
    1. scale_factor = total_assets の current_value
    2. 候補指標（固定6除外、欠損除外）について二段階閾値で絞り込み
    3. スコアで並べて上位3件

    Returns:
        (top_changes_list, error_message)
    """
    # scale_factor の取得
    total_assets_data = current_facts.get("total_assets", {})
    scale_factor_val = total_assets_data.get("value")

    if scale_factor_val is None:
        return [], "総資産（scale_factor）が未取得のため、変化大抽出は実行できません（情報不足）"

    try:
        scale_factor = Decimal(str(scale_factor_val))
    except (InvalidOperation, ValueError):
        return [], "総資産（scale_factor）が未取得のため、変化大抽出は実行できません（情報不足）"

    if scale_factor == 0:
        return [], "総資産（scale_factor）が0のため、変化大抽出は実行できません"

    # 候補指標の収集（固定6を除外）
    # helper指標（equity等）も除外
    helper_keys = {"equity"}
    candidate_keys = set(current_facts.keys()) | set(prev_facts.keys())
    candidate_keys -= set(fixed_keys)
    candidate_keys -= helper_keys

    scored_items = []

    for key in candidate_keys:
        current_data = current_facts.get(key, {})
        prev_data = prev_facts.get(key, {})
        current_val = current_data.get("value")
        prev_val = prev_data.get("value")

        # 欠損除外
        if current_val is None or prev_val is None:
            continue

        try:
            cv = Decimal(str(current_val))
            pv = Decimal(str(prev_val))
        except (InvalidOperation, ValueError):
            continue

        delta = cv - pv
        abs_delta = abs(delta)

        # delta_pct
        delta_pct = None
        if pv != 0:
            delta_pct = delta / pv

        # ---- 二段階閾値 ----
        # A（相対条件）: abs(delta) / scale_factor >= 0.5%
        passes_a = (abs_delta / scale_factor) >= THRESHOLD_A_RATIO

        # B（率条件）: abs(prev) / scale_factor >= 1% かつ abs(delta_pct) >= 10%
        passes_b = False
        if delta_pct is not None:
            prev_relative = abs(pv) / scale_factor
            if prev_relative >= THRESHOLD_B_PREV_MIN:
                if abs(delta_pct) >= THRESHOLD_B_PCT:
                    passes_b = True

        if not passes_a and not passes_b:
            continue

        # ---- スコア計算 ----
        pct_part = abs(delta_pct) if delta_pct is not None else Decimal("0")
        # pct_part 上限クリップ
        if pct_part > PCT_CLIP_MAX:
            pct_part = PCT_CLIP_MAX

        norm_part = abs_delta / scale_factor

        score = float(pct_part * Decimal("0.6") + norm_part * Decimal("0.4"))

        # カテゴリ取得
        config = _get_metric_config(key)
        category = config.get("category", "BS") if config else "BS"
        cat_priority = CATEGORY_PRIORITY.get(category, 2)
        label = config["metric_label"] if config else key

        scored_items.append({
            "metric_key": key,
            "metric_label": label,
            "current_value": str(cv),
            "prev_value": str(pv),
            "delta": str(delta),
            "delta_pct": float(delta_pct) if delta_pct is not None else None,
            "score": score,
            "cat_priority": cat_priority,
            "norm_part": float(norm_part),
            "unit": current_data.get("unit", "—"),
            "consolidation_scope": current_data.get("consolidation_scope", "—"),
            "source_locator": current_data.get("source_locator", "—"),
            "category": category,
        })

    # ---- 並べ替え ----
    # score 降順 → カテゴリ優先（PL > CF > BS）→ norm_part 降順
    scored_items.sort(key=lambda x: (-x["score"], x["cat_priority"], -x["norm_part"]))

    # 上位3件
    top = scored_items[:3]

    # 表示用に不要なフィールドを削除
    for item in top:
        del item["score"]
        del item["cat_priority"]
        del item["norm_part"]

    return top, None


# ==============================================================
# メイン生成処理
# ==============================================================

def generate_diff_summary(db: Session, doc_id: str) -> Dict[str, Any]:
    """
    指定された doc_id の差分サマリーを生成し、DB に保存する。
    
    Returns:
        差分データ全体の辞書
    """
    notes_list = []
    status = "ok"

    try:
        # 1. 現在の書類を取得
        current_doc = db.query(EdinetDocument).filter(
            EdinetDocument.doc_id == doc_id
        ).first()

        if not current_doc:
            return _failed_result(db, doc_id, "指定された書類が見つかりません")

        # 2. facts_snapshot を構築
        current_facts = build_facts_snapshot(db, doc_id)
        if not current_facts:
            return _failed_result(db, doc_id, "財務データが取得できません")

        # 3. prev を決定
        current_scope = _get_doc_scope(db, doc_id)
        prev_doc = find_prev_doc(db, current_doc, current_scope)

        prev_facts = None
        prev_doc_id = None
        scope_mismatch = False

        if prev_doc:
            prev_doc_id = prev_doc.doc_id
            prev_facts = build_facts_snapshot(db, prev_doc_id)
            
            # consolidation_scope 不一致チェック
            prev_scope = _get_doc_scope(db, prev_doc_id)
            if current_scope and prev_scope and current_scope != prev_scope:
                scope_mismatch = True
                notes_list.append("注意：連結/個別の区分が一致しない可能性があります")

        # 4. 固定6項目の差分計算
        fixed_six, fixed_notes = compute_fixed_six(current_facts, prev_facts)
        notes_list.extend(fixed_notes)

        # 5. 変化大3件の抽出
        top_changes = []
        top_changes_error = None
        if prev_facts:
            top_changes, top_changes_error = extract_top_changes(
                current_facts, prev_facts, FIXED_SIX_KEYS
            )
            if top_changes_error:
                notes_list.append(top_changes_error)

        # 6. 欠損チェック → status 判定
        has_missing = any(item["is_missing"] for item in fixed_six)
        if has_missing:
            status = "partial"

        # 7. JSON ペイロード構築
        payload = {
            "current_doc_id": doc_id,
            "prev_doc_id": prev_doc_id,
            "current_submit_date": str(current_doc.submit_datetime or current_doc.target_date or "—"),
            "current_period": _format_period(current_doc),
            "prev_submit_date": None,
            "prev_period": None,
            "scope_mismatch": scope_mismatch,
            "has_prev": prev_doc is not None,
            "fixed_six": fixed_six,
            "top_changes": top_changes,
            "top_changes_error": top_changes_error,
            "filer_name": current_doc.filer_name or "—",
        }

        if prev_doc:
            payload["prev_submit_date"] = str(prev_doc.submit_datetime or prev_doc.target_date or "—")
            payload["prev_period"] = _format_period(prev_doc)

        # 8. DB に保存
        notes_text = "\n".join(notes_list) if notes_list else None
        _save_diff_summary(db, doc_id, prev_doc_id, status, payload, notes_text)

        payload["status"] = status
        payload["notes"] = notes_text
        payload["generated_at"] = datetime.now().isoformat()

        return payload

    except Exception as e:
        logger.error(f"差分生成失敗 doc_id={doc_id}: {e}", exc_info=True)
        return _failed_result(db, doc_id, f"差分生成処理でエラーが発生: {e}")


def _format_period(doc: EdinetDocument) -> str:
    """期間をフォーマットする"""
    ps = doc.period_start
    pe = doc.period_end
    if ps and pe:
        return f"{ps} ～ {pe}"
    elif pe:
        return f"～ {pe}"
    return "—"


def _failed_result(db: Session, doc_id: str, error_msg: str) -> Dict[str, Any]:
    """失敗結果を返す（DB にも保存）"""
    _save_diff_summary(db, doc_id, None, "failed", None, error_msg)
    return {
        "status": "failed",
        "current_doc_id": doc_id,
        "notes": error_msg,
        "generated_at": datetime.now().isoformat(),
    }


def _save_diff_summary(
    db: Session,
    current_doc_id: str,
    prev_doc_id: Optional[str],
    status: str,
    payload: Optional[Dict],
    notes: Optional[str],
) -> None:
    """差分サマリーを DB に保存（既存があれば更新）"""
    try:
        existing = db.query(EdinetDiffSummary).filter(
            EdinetDiffSummary.current_doc_id == current_doc_id
        ).first()

        if existing:
            existing.prev_doc_id = prev_doc_id
            existing.status = status
            existing.json_payload = payload
            existing.notes = notes
            existing.generated_at = datetime.now()
        else:
            summary = EdinetDiffSummary(
                current_doc_id=current_doc_id,
                prev_doc_id=prev_doc_id,
                status=status,
                json_payload=payload,
                notes=notes,
            )
            db.add(summary)

        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"diff_summary 保存失敗: {e}")


# ==============================================================
# キャッシュ付き取得
# ==============================================================

def get_or_generate_diff(db: Session, doc_id: str, force: bool = False) -> Dict[str, Any]:
    """
    キャッシュ済みの差分があればそれを返し、無ければ生成する。
    
    Args:
        db: DB セッション
        doc_id: 対象書類 ID
        force: True の場合、キャッシュを無視して再生成
    
    Returns:
        差分データの辞書
    """
    if not force:
        # キャッシュを確認
        cached = db.query(EdinetDiffSummary).filter(
            EdinetDiffSummary.current_doc_id == doc_id
        ).first()

        if cached:
            result = cached.json_payload or {}
            result["status"] = cached.status
            result["notes"] = cached.notes
            result["generated_at"] = str(cached.generated_at) if cached.generated_at else "—"
            result["current_doc_id"] = doc_id
            result["prev_doc_id"] = cached.prev_doc_id
            return result

    # キャッシュなし or 強制再生成
    return generate_diff_summary(db, doc_id)
