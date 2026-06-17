"""
EDINET 日次バッチサービス

1日100リクエストのバジェット内で、銘柄情報を自動取得する。
3フェーズ構成:
  Phase A: 日次スキャン — 直近N日の書類メタデータを取得
  Phase B: シード銘柄処理 — 未処理の有報/四半期報をDL & 解析
  Phase C: バックフィル — 余剰バジェットで過去日付を遡る

使用するAPIエンドポイント:
  - documents.json?date=YYYY-MM-DD (1リクエスト/日付)
  - documents/{docID}?type=1      (1リクエスト/書類、XBRL ZIP)
"""

import os
import sys
import time
import json
import yaml
import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func

# プロジェクトルートをパスに追加
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database import SessionLocal
from models.edinet_document import EdinetDocument
from models.edinet_file import EdinetFile
from models.edinet_batch_log import EdinetBatchLog
from models.company_info import CompanyInfo
from models.master import StockMaster

logger = logging.getLogger("edinet_daily_batch")


# =====================================================
# APIバジェットマネージャ
# =====================================================


class ApiBudgetManager:
    """
    1日のAPIリクエスト消費を追跡・制御するマネージャ。
    バジェット超過時にはリクエストをブロックする。
    """

    def __init__(self, db: Session, batch_date: date, daily_limit: int = 100):
        self.db = db
        self.batch_date = batch_date
        self.daily_limit = daily_limit
        # DB から当日の既存消費を集計
        self._used = self._load_used_today()

    def _load_used_today(self) -> int:
        """当日のバッチログから既に消費済みのAPIコール数を取得"""
        result = (
            self.db.query(sa_func.coalesce(sa_func.sum(EdinetBatchLog.api_calls), 0))
            .filter(EdinetBatchLog.batch_date == self.batch_date)
            .scalar()
        )
        return int(result)

    @property
    def used(self) -> int:
        """消費済みリクエスト数"""
        return self._used

    @property
    def remaining(self) -> int:
        """残りバジェット"""
        return max(0, self.daily_limit - self._used)

    def can_consume(self, count: int = 1) -> bool:
        """指定数のリクエストを消費できるかチェック"""
        return self._used + count <= self.daily_limit

    def consume(self, count: int = 1) -> bool:
        """
        バジェットを消費する。
        上限超過の場合は False を返し、消費しない。
        """
        if not self.can_consume(count):
            logger.warning(
                f"バジェット超過: 残り {self.remaining} に対して {count} 消費しようとしました"
            )
            return False
        self._used += count
        return True

    def summary(self) -> str:
        """バジェット状況のサマリー文字列"""
        return (
            f"API Budget: {self._used}/{self.daily_limit} ({self.remaining} remaining)"
        )


# =====================================================
# メインバッチサービス
# =====================================================


class EdinetDailyBatchService:
    """
    EDINET 日次バッチの中核ロジック。
    Phase A → B → C を順に実行し、バジェット内で最大限のデータを取得する。
    """

    def __init__(
        self,
        db: Optional[Session] = None,
        config_path: Optional[str] = None,
        dry_run: bool = False,
        budget_override: Optional[int] = None,
    ):
        self.db = db or SessionLocal()
        self.dry_run = dry_run
        self.config = self._load_config(config_path)

        # バジェットマネージャ初期化
        daily_limit = budget_override or self.config.get("daily_budget", 100)
        self.budget = None  # run() 内で初期化
        self._daily_limit = daily_limit

        # EDINETクライアント（同期版を使用）
        from services.edinet_service import EdinetClient

        self.edinet_client = EdinetClient()

        # ストレージサービス
        from services.edinet_storage import EdinetStorageService

        self.storage = EdinetStorageService(db=self.db)

        # 設定パラメータ
        self.scan_days = self.config.get("scan_days", 5)
        self.request_interval = self.config.get("request_interval_sec", 2.0)
        self.priority_doc_types = self.config.get("priority_doc_types", ["120", "140"])
        self.backfill_max_days = self.config.get("backfill_max_days", 365)
        self.backfill_start_date = self.config.get("backfill_start_date", "2024-01-01")
        self.download_xbrl = self.config.get("download_xbrl", True)
        self.download_pdf = self.config.get("download_pdf", False)
        self.process_highlights = self.config.get("process_highlights", True)
        self.process_derived = self.config.get("process_derived", True)

        # シード銘柄マッピング
        self.seed_edinet_map = self.config.get("seed_edinet_map", {})

    def _load_config(self, config_path: Optional[str] = None) -> dict:
        """設定ファイルを読み込む"""
        if not config_path:
            config_path = os.path.join(
                PROJECT_ROOT, "config", "edinet_batch_config.yml"
            )
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            logger.warning(
                f"設定ファイルが見つかりません: {config_path}。デフォルト設定を使用します。"
            )
            return {}

    # -------------------------------------------------
    # メイン実行
    # -------------------------------------------------

    def run(self, target_date: Optional[date] = None):
        """
        バッチのメインエントリーポイント。
        Phase A → B → C を順に実行する。
        """
        target_date = target_date or date.today()
        self.budget = ApiBudgetManager(self.db, target_date, self._daily_limit)

        print(f"{'='*60}")
        print(f"  EDINET 日次バッチ: {target_date}")
        print(f"  モード: {'ドライラン' if self.dry_run else '本番実行'}")
        print(f"  {self.budget.summary()}")
        print(f"{'='*60}\n")

        try:
            # Phase A: 日次スキャン
            self._run_phase("A", target_date, self._phase_a_scan_dates)

            # Phase B: シード銘柄処理
            self._run_phase("B", target_date, self._phase_b_process_seed_stocks)

            # Phase C: バックフィル
            self._run_phase("C", target_date, self._phase_c_backfill)

        except Exception as e:
            logger.error(f"バッチ実行中にエラー: {e}", exc_info=True)
            print(f"\n!!! バッチエラー: {e}")

        print(f"\n{'='*60}")
        print(f"  バッチ完了: {self.budget.summary()}")
        print(f"{'='*60}")

    def _run_phase(self, phase: str, target_date: date, func):
        """フェーズを実行し、結果をバッチログに記録する"""
        phase_names = {"A": "日次スキャン", "B": "シード銘柄処理", "C": "バックフィル"}
        phase_name = phase_names.get(phase, phase)

        if self.budget.remaining <= 0:
            print(
                f"\n--- Phase {phase} ({phase_name}): スキップ（バジェット残なし）---"
            )
            self._save_batch_log(target_date, phase, 0, 0, 0, 0, 0, "SKIPPED")
            return

        print(f"\n--- Phase {phase} ({phase_name}) 開始 ---")
        print(f"    {self.budget.summary()}")

        # バッチログの開始記録
        log = EdinetBatchLog(
            batch_date=target_date,
            phase=phase,
            status="RUNNING",
            started_at=datetime.now(),
        )
        self.db.add(log)
        self.db.commit()

        budget_before = self.budget.used

        try:
            result = func(target_date)
            log.status = "DONE"
        except Exception as e:
            logger.error(f"Phase {phase} エラー: {e}", exc_info=True)
            # セッションの状態を回復
            self.db.rollback()
            log.status = "FAILED"
            log.detail_json = {"error": str(e)}
            result = {}
            # ログ記録のために再度addする（rollback で detach されるため）
            self.db.add(log)

        # 統計を記録
        # ドライラン時はAPIコールを0として記録（次回の本番実行に影響しないようにする）
        actual_api_calls = self.budget.used - budget_before
        log.api_calls = 0 if self.dry_run else actual_api_calls
        log.docs_found = result.get("docs_found", 0)
        log.docs_downloaded = result.get("docs_downloaded", 0)
        log.docs_processed = result.get("docs_processed", 0)
        log.errors = result.get("errors", 0)
        log.finished_at = datetime.now()

        if result.get("detail"):
            log.detail_json = result["detail"]

        try:
            self.db.commit()
        except Exception:
            self.db.rollback()

        print(
            f"--- Phase {phase} 完了: API={log.api_calls}回, "
            f"発見={log.docs_found}, DL={log.docs_downloaded}, "
            f"処理={log.docs_processed}, エラー={log.errors} ---"
        )

    def _save_batch_log(
        self,
        batch_date,
        phase,
        api_calls,
        docs_found,
        docs_downloaded,
        docs_processed,
        errors,
        status,
    ):
        """バッチログを保存するヘルパー"""
        log = EdinetBatchLog(
            batch_date=batch_date,
            phase=phase,
            api_calls=api_calls,
            docs_found=docs_found,
            docs_downloaded=docs_downloaded,
            docs_processed=docs_processed,
            errors=errors,
            status=status,
            started_at=datetime.now(),
            finished_at=datetime.now(),
        )
        self.db.add(log)
        self.db.commit()

    # -------------------------------------------------
    # Phase A: 日次スキャン
    # -------------------------------------------------

    def _phase_a_scan_dates(self, target_date: date) -> dict:
        """
        直近N日分の documents.json を取得し、
        全書類メタデータを edinet_documents に UPSERT する。
        """
        stats = {"docs_found": 0, "errors": 0, "detail": {"scanned_dates": []}}

        for i in range(self.scan_days):
            scan_date = target_date - timedelta(days=i)

            # 土日はEDINET提出がないためスキップ
            if scan_date.weekday() >= 5:
                continue

            # 既にスキャン済みか確認（当日分以外は再スキャンしない）
            if i > 0:
                existing_count = (
                    self.db.query(EdinetDocument)
                    .filter(EdinetDocument.target_date == scan_date)
                    .count()
                )
                if existing_count > 0:
                    print(
                        f"    {scan_date}: スキャン済み ({existing_count}件). スキップ"
                    )
                    continue

            # バジェットチェック
            if not self.budget.can_consume():
                print(f"    バジェット切れ。スキャン中断。")
                break

            # APIコール
            print(f"    {scan_date}: documents.json 取得中...")
            if self.dry_run:
                print(f"    [DRY-RUN] APIコールをスキップ")
                self.budget.consume()
                continue

            try:
                docs_list = self.edinet_client.get_documents_by_date(
                    scan_date, type_code=2
                )
                self.budget.consume()
                time.sleep(self.request_interval)

                if docs_list:
                    # edinet_documents に UPSERT
                    upserted = self._upsert_documents(scan_date, docs_list)
                    stats["docs_found"] += upserted
                    stats["detail"]["scanned_dates"].append(
                        {"date": str(scan_date), "count": upserted}
                    )
                    print(f"    {scan_date}: {upserted}件の書類を取得")

                    # CompanyInfo 自動補完
                    self._auto_populate_company_info(docs_list)
                else:
                    print(f"    {scan_date}: 書類なし")
                    stats["detail"]["scanned_dates"].append(
                        {"date": str(scan_date), "count": 0}
                    )

            except Exception as e:
                logger.error(f"Phase A スキャンエラー ({scan_date}): {e}")
                stats["errors"] += 1
                print(f"    {scan_date}: エラー - {e}")

        return stats

    # -------------------------------------------------
    # Phase B: シード銘柄処理
    # -------------------------------------------------

    def _phase_b_process_seed_stocks(self, target_date: date) -> dict:
        """
        シード銘柄リストの未処理書類をダウンロード & 解析する。
        優先順位: 有報(120) > 四半期報(140) > 半期報(160)、新しい順
        """
        stats = {
            "docs_found": 0,
            "docs_downloaded": 0,
            "docs_processed": 0,
            "errors": 0,
            "detail": {"processed_stocks": []},
        }

        # シード銘柄の sec_code リスト（4桁 + "0"）
        seed_sec_codes = [code + "0" for code in self.seed_edinet_map.keys()]

        # edinet_documents から対象書類を検索
        target_docs = (
            self.db.query(EdinetDocument)
            .filter(
                EdinetDocument.sec_code.in_(seed_sec_codes),
                EdinetDocument.doc_type_code.in_(self.priority_doc_types),
                EdinetDocument.xbrl_flag == "1",  # XBRLがあるもの
            )
            .order_by(
                # 有報を優先（doc_type_code 昇順：120 < 140）
                EdinetDocument.doc_type_code,
                # 新しい順
                EdinetDocument.submit_datetime.desc(),
            )
            .all()
        )

        stats["docs_found"] = len(target_docs)
        print(f"    シード銘柄の対象書類: {len(target_docs)}件")

        for doc in target_docs:
            if not self.budget.can_consume():
                print(f"    バジェット切れ。処理中断。")
                break

            # 既にダウンロード済みか確認
            existing_file = (
                self.db.query(EdinetFile)
                .filter(
                    EdinetFile.doc_id == doc.doc_id,
                    EdinetFile.file_type == "ZIP_TYPE1",
                    EdinetFile.status == "OK",
                )
                .first()
            )

            if existing_file:
                # ファイルが実在するか確認
                abs_path = self.storage.get_absolute_path(existing_file.storage_path)
                if abs_path.exists():
                    continue  # スキップ（DL済み）

            # ダウンロード実行
            stock_code = doc.sec_code[:4] if doc.sec_code else "-"
            print(
                f"    DL: {doc.doc_id} ({doc.filer_name}) [{stock_code}] "
                f"type={doc.doc_type_code} period={doc.period_end}"
            )

            if self.dry_run:
                print(f"    [DRY-RUN] DLをスキップ")
                self.budget.consume()
                stats["docs_downloaded"] += 1
                continue

            try:
                content = self.edinet_client.fetch_document_content_zip(doc.doc_id)
                self.budget.consume()
                time.sleep(self.request_interval)

                if content:
                    # ファイル保存
                    date_ref = (
                        doc.submit_datetime
                        if doc.submit_datetime
                        else datetime.combine(doc.target_date, datetime.min.time())
                    )
                    self.storage.save_raw_file(
                        doc_id=doc.doc_id,
                        date_obj=date_ref,
                        file_type="ZIP_TYPE1",
                        content=content,
                        submitter_code=doc.edinet_code,
                        doc_type_code=doc.doc_type_code,
                        period_end=doc.period_end,
                    )
                    stats["docs_downloaded"] += 1
                    print(f"      → 保存OK ({len(content):,} bytes)")

                    # XBRL解析 & 財務ハイライト抽出
                    if self.process_highlights:
                        processed = self._process_xbrl_highlights(doc.doc_id)
                        if processed:
                            stats["docs_processed"] += 1

                    stats["detail"]["processed_stocks"].append(
                        {
                            "stock_code": stock_code,
                            "doc_id": doc.doc_id,
                            "doc_type": doc.doc_type_code,
                            "period_end": (
                                str(doc.period_end) if doc.period_end else "-"
                            ),
                        }
                    )
                else:
                    print(f"      → DL失敗（空レスポンス）")
                    stats["errors"] += 1

            except Exception as e:
                logger.error(f"Phase B DLエラー ({doc.doc_id}): {e}")
                stats["errors"] += 1
                print(f"      → エラー: {e}")

        return stats

    # -------------------------------------------------
    # Phase C: バックフィル
    # -------------------------------------------------

    def _phase_c_backfill(self, target_date: date) -> dict:
        """
        余剰バジェットで過去日付の documents.json をスキャンし、
        未取得の書類メタデータを蓄積する。
        """
        stats = {"docs_found": 0, "errors": 0, "detail": {"scanned_dates": []}}

        if self.budget.remaining <= 0:
            print("    バジェット残なし。バックフィルをスキップ。")
            return stats

        # バックフィル開始日
        try:
            start_date = datetime.strptime(self.backfill_start_date, "%Y-%m-%d").date()
        except ValueError:
            start_date = date(2024, 1, 1)

        # スキャン済みの日付を取得
        scanned_dates = set()
        existing_dates = self.db.query(EdinetDocument.target_date).distinct().all()
        for (d,) in existing_dates:
            scanned_dates.add(d)

        # 未スキャンの日付を生成（直近から遡る）
        # Phase A でスキャン済みの範囲はスキップ
        backfill_start = target_date - timedelta(days=self.scan_days + 1)
        candidate_dates = []

        current = backfill_start
        while current >= start_date and len(candidate_dates) < self.backfill_max_days:
            # 土日スキップ
            if current.weekday() < 5 and current not in scanned_dates:
                candidate_dates.append(current)
            current -= timedelta(days=1)

        print(f"    未スキャン日付: {len(candidate_dates)}件")
        print(f"    残りバジェット: {self.budget.remaining}")

        for scan_date in candidate_dates:
            if not self.budget.can_consume():
                print(f"    バジェット切れ。バックフィル中断。")
                break

            print(f"    {scan_date}: documents.json 取得中...")

            if self.dry_run:
                print(f"    [DRY-RUN] APIコールをスキップ")
                self.budget.consume()
                continue

            try:
                docs_list = self.edinet_client.get_documents_by_date(
                    scan_date, type_code=2
                )
                self.budget.consume()
                time.sleep(self.request_interval)

                if docs_list:
                    upserted = self._upsert_documents(scan_date, docs_list)
                    stats["docs_found"] += upserted
                    stats["detail"]["scanned_dates"].append(
                        {"date": str(scan_date), "count": upserted}
                    )
                    print(f"    {scan_date}: {upserted}件")

                    # CompanyInfo 自動補完
                    self._auto_populate_company_info(docs_list)
                else:
                    stats["detail"]["scanned_dates"].append(
                        {"date": str(scan_date), "count": 0}
                    )

            except Exception as e:
                logger.error(f"Phase C エラー ({scan_date}): {e}")
                stats["errors"] += 1

        return stats

    # -------------------------------------------------
    # 共通ヘルパー
    # -------------------------------------------------

    def _upsert_documents(self, target_date: date, docs_list: list) -> int:
        """documents.json のレスポンスを edinet_documents に UPSERT"""
        count = 0
        for data in docs_list:
            try:
                doc_id = data.get("docID")
                if not doc_id:
                    continue

                # 日付パース
                def p_date(s):
                    return datetime.strptime(s, "%Y-%m-%d").date() if s else None

                # 既存チェック
                existing = (
                    self.db.query(EdinetDocument).filter_by(doc_id=doc_id).first()
                )

                if existing:
                    # フィールド更新（主要なもののみ）
                    if data.get("secCode"):
                        existing.sec_code = data["secCode"]
                    if data.get("edinetCode"):
                        existing.edinet_code = data["edinetCode"]
                    if data.get("docTypeCode"):
                        existing.doc_type_code = data["docTypeCode"]
                else:
                    # 新規作成
                    submit_dt = None
                    if data.get("submitDateTime"):
                        try:
                            submit_dt = datetime.strptime(
                                data["submitDateTime"], "%Y-%m-%d %H:%M"
                            )
                        except ValueError:
                            pass

                    new_doc = EdinetDocument(
                        doc_id=doc_id,
                        target_date=target_date,
                        edinet_code=data.get("edinetCode"),
                        sec_code=data.get("secCode"),
                        jcn=data.get("JCN"),
                        filer_name=data.get("filerName"),
                        doc_type_code=data.get("docTypeCode"),
                        form_code=data.get("formCode"),
                        doc_description=data.get("docDescription"),
                        period_start=p_date(data.get("periodStart")),
                        period_end=p_date(data.get("periodEnd")),
                        submit_datetime=submit_dt,
                        withdrawal_status=data.get("withdrawalStatus"),
                        doc_info_edit_status=data.get("docInfoEditStatus"),
                        disclosure_status=data.get("disclosureStatus"),
                        xbrl_flag=data.get("xbrlFlag"),
                        pdf_flag=data.get("pdfFlag"),
                        attach_doc_flag=data.get("attachDocFlag"),
                        english_doc_flag=data.get("englishDocFlag"),
                        csv_flag=data.get("csvFlag"),
                    )
                    self.db.add(new_doc)
                    count += 1

                # 100件ごとにコミット（メモリ節約）
                if count > 0 and count % 100 == 0:
                    self.db.commit()

            except Exception as e:
                logger.error(f"Document UPSERT エラー ({data.get('docID')}): {e}")

        self.db.commit()
        return count

    def _auto_populate_company_info(self, docs_list: list):
        """
        書類メタデータから CompanyInfo を自動補完する。
        sec_code が判明している書類のうち、CompanyInfo が未登録のものを作成。
        begin_nested() (SAVEPOINT) を使用し、個別の失敗がセッション全体に影響しないようにする。
        """
        for data in docs_list:
            sec_code = data.get("secCode")
            edinet_code = data.get("edinetCode")
            filer_name = data.get("filerName")

            if not sec_code or not edinet_code:
                continue

            stock_code = sec_code[:4]  # 5桁 → 4桁

            # StockMaster に存在しない場合はスキップ
            master = (
                self.db.query(StockMaster)
                .filter(StockMaster.code == stock_code)
                .first()
            )
            if not master:
                continue

            # CompanyInfo 既存チェック（stock_code で検索）
            existing_by_code = (
                self.db.query(CompanyInfo)
                .filter(CompanyInfo.stock_code == stock_code)
                .first()
            )

            if existing_by_code:
                # 既に存在する → スキップ
                continue

            # edinet_code が既に別の stock_code で使用されていないか確認
            existing_by_edinet = (
                self.db.query(CompanyInfo)
                .filter(CompanyInfo.edinet_code == edinet_code)
                .first()
            )
            if existing_by_edinet:
                continue

            # SAVEPOINT を使って個別のINSERTを保護
            try:
                nested = self.db.begin_nested()
                new_company = CompanyInfo(
                    stock_code=stock_code,
                    edinet_code=edinet_code,
                    corporate_name_ja=filer_name or master.name,
                )
                self.db.add(new_company)
                nested.commit()
                logger.info(f"CompanyInfo 自動作成: {stock_code} ({filer_name})")
            except Exception:
                # SAVEPOINT のみロールバック（外側のトランザクションは健全なまま）
                nested.rollback()

        # 全体をコミット
        self.db.commit()

    def _process_xbrl_highlights(self, doc_id: str) -> bool:
        """
        ダウンロード済みのXBRLから財務ハイライトを抽出する。
        既存の financial_processor を活用。
        """
        try:
            from services.financial_processor import FinancialProcessor

            processor = FinancialProcessor(db=self.db)
            processor.process_document(doc_id)
            logger.info(f"XBRL処理完了: {doc_id}")
            return True
        except ImportError:
            logger.warning("FinancialProcessor が利用不可。XBRL処理をスキップ。")
            return False
        except Exception as e:
            logger.error(f"XBRL処理エラー ({doc_id}): {e}")
            return False
