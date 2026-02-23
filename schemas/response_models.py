"""
FastAPI レスポンスモデル定義。

各 JSON 返却エンドポイントの戻り値型を Pydantic モデルで宣言する。
FastAPI 0.131.0 仕様に準拠。
"""

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


# ==============================================================
# stocks ルーター
# ==============================================================

class StockSearchResponse(BaseModel):
    """銘柄検索 API のレスポンス"""
    suggestions: List[str] = Field(
        ..., description="オートコンプリート候補（'銘柄名（コード）' 形式）"
    )


# ==============================================================
# edinet ルーター
# ==============================================================

class EdinetDocumentItem(BaseModel):
    """EDINET 書類一覧の個別アイテム"""
    # EDINET API のレスポンスはフィールドが多いため Any で受ける
    model_config = {"extra": "allow"}

class EdinetDocumentsResponse(BaseModel):
    """EDINET 書類一覧のレスポンス"""
    date: str = Field(..., description="検索日（YYYY-MM-DD）")
    count: int = Field(..., description="件数")
    documents: List[Dict[str, Any]] = Field(
        default_factory=list, description="書類リスト"
    )

class EdinetHealthResponse(BaseModel):
    """EDINET ヘルスチェックのレスポンス"""
    ok: bool = Field(..., description="サービス稼働状態")
    has_api_key: bool = Field(..., description="API キーの有無")


# ==============================================================
# edinet_docs ルーター
# ==============================================================

class EdinetDownloadResponse(BaseModel):
    """書類ダウンロード結果のレスポンス"""
    doc_id: str = Field(..., description="書類 ID")
    saved_zip: str = Field(..., description="保存された ZIP パス")
    unzipped_dir: str = Field(..., description="展開先ディレクトリ")
    xbrl_files: List[str] = Field(
        default_factory=list, description="検出された XBRL ファイル一覧"
    )
    inline_xbrl_files: List[str] = Field(
        default_factory=list, description="検出されたインライン XBRL ファイル一覧"
    )
    primary_xbrl: Optional[str] = Field(
        None, description="プライマリ XBRL ファイルパス"
    )

class EdinetFinancialsResponse(BaseModel):
    """財務データ抽出結果のレスポンス"""
    doc_id: str = Field(..., description="書類 ID")
    primary_xbrl: Optional[str] = Field(
        None, description="使用した XBRL ファイルパス"
    )
    financials: Dict[str, Any] = Field(
        default_factory=dict, description="抽出された財務データ"
    )
    note: Optional[str] = Field(None, description="備考")


# ==============================================================
# fundamentals ルーター
# ==============================================================

class FundamentalMetaInfo(BaseModel):
    """ファンダメンタル分析のメタ情報"""
    notes: Optional[str] = None
    warning: Optional[str] = None

class EdinetFundamentalResponse(BaseModel):
    """EDINET ファンダメンタルデータのレスポンス"""
    doc_id: str = Field(..., description="書類 ID")
    sec_code: Optional[str] = Field(None, description="証券コード")
    financials: Dict[str, Any] = Field(
        default_factory=dict, description="財務ハイライト"
    )
    market: Optional[Dict[str, Any]] = Field(
        None, description="市場データ（J-Quants 経由）"
    )
    ratios: Optional[Dict[str, Any]] = Field(
        None, description="算出指標（ROE, PER, PBR 等）"
    )
    meta: FundamentalMetaInfo = Field(
        default_factory=FundamentalMetaInfo, description="メタ情報"
    )
