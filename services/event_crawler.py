"""
EDINETイベント巡回ジョブ

EDINET API v2のdocuments.jsonを日付単位で巡回し、
イベントを抽出してDBに保存する。

絶対遵守ポリシー:
- EDINET公式API（v2）のみ使用
- Web画面HTMLは一切取得しない
- レート制御（リクエスト間1秒待機、失敗時指数バックオフ）
- 1実行あたり最大30日分
- 冪等設計（event_ingest_stateで管理）
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session

from services.event_source_checker import EventSourceChecker, SourcePolicyError
from services.event_extractor import EventExtractor
from models.event_source_policy import EventIngestState
from models.stock_impact import StockEvent, StockEventAnalysis

logger = logging.getLogger(__name__)

# ============================================================
# 定数
# ============================================================

# レート制御: リクエスト間の最小待機秒数
REQUEST_INTERVAL_SEC = 1.0

# 1実行あたりの最大巡回日数
MAX_CRAWL_DAYS = 30

# ファイル保存ルート
STORAGE_ROOT = Path("D:/edinet_data")


class EdinetEventCrawler:
    """EDINET APIからイベントを巡回・抽出するクローラー"""

    def __init__(self, db: Session, dry_run: bool = False):
        self.db = db
        self.dry_run = dry_run
        self.extractor = EventExtractor()
        self.source_checker = EventSourceChecker(db)
        self.source_name = "EDINET_API"

        # 統計
        self.stats = {
            "days_processed": 0,
            "days_skipped": 0,
            "documents_fetched": 0,
            "events_extracted": 0,
            "events_saved": 0,
            "errors": 0,
        }

    async def crawl(
        self, days: int = 7, start_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        EDINET APIを日付単位で巡回し、イベントを抽出・保存する。

        Args:
            days: 巡回日数（デフォルト7日）
            start_date: 開始日（Noneの場合は今日から遡る）

        Returns:
            実行統計
        """
        # 日数制限
        actual_days = min(days, MAX_CRAWL_DAYS)
        if days > MAX_CRAWL_DAYS:
            logger.warning(f"巡回日数を{MAX_CRAWL_DAYS}日に制限: 要求={days}")

        # ソースポリシーチェック
        try:
            self.source_checker.check_source_allowed(self.source_name)
        except SourcePolicyError as e:
            logger.error(f"ソースポリシーエラー: {e}")
            return {"error": str(e), **self.stats}

        # 日付範囲を計算
        end_date = start_date or date.today()
        dates = [end_date - timedelta(days=i) for i in range(actual_days)]

        logger.info(f"EDINET巡回開始: {dates[-1]} ～ {dates[0]} ({len(dates)}日間)")

        # 既存のEdinetClient（async httpx）を使用
        from services.edinet_client import EdinetClient

        client = EdinetClient()

        try:
            for target_date in dates:
                await self._process_date(client, target_date)
                # レート制御
                await asyncio.sleep(REQUEST_INTERVAL_SEC)
        finally:
            await client.close()

        logger.info(f"EDINET巡回完了: {self.stats}")
        return self.stats

    async def _process_date(self, client, target_date: date) -> None:
        """1日分のEDINETドキュメントを処理する"""
        date_str = target_date.strftime("%Y-%m-%d")

        # 冪等チェック: 既にDONEなら即スキップ
        existing_state = (
            self.db.query(EventIngestState)
            .filter(
                EventIngestState.source_name == self.source_name,
                EventIngestState.ingest_date == target_date,
            )
            .first()
        )

        if existing_state and existing_state.status == "DONE":
            logger.debug(f"スキップ（処理済み）: {date_str}")
            self.stats["days_skipped"] += 1
            return

        # 処理状態を記録
        if not existing_state:
            existing_state = EventIngestState(
                source_name=self.source_name,
                ingest_date=target_date,
                status="PROCESSING",
                started_at=datetime.now(),
            )
            self.db.add(existing_state)
        else:
            existing_state.status = "PROCESSING"
            existing_state.started_at = datetime.now()
            existing_state.error_message = None

        self.db.commit()

        try:
            # EDINET APIからドキュメント一覧取得
            logger.info(f"EDINET API取得: {date_str}")
            response = await client.get_documents(date_str, type_code=2)
            results = response.get("results", [])

            existing_state.fetched_count = len(results)
            self.stats["documents_fetched"] += len(results)

            # 各ドキュメントからイベント抽出
            extracted_count = 0
            for doc in results:
                events = self.extractor.extract_events(doc)
                for event_data in events:
                    saved = self._save_event(event_data)
                    if saved:
                        extracted_count += 1
                        self.stats["events_saved"] += 1
                    self.stats["events_extracted"] += 1

            existing_state.extracted_count = extracted_count
            existing_state.status = "DONE"
            existing_state.completed_at = datetime.now()
            self.stats["days_processed"] += 1

            self.db.commit()
            logger.info(
                f"完了: {date_str} (文書={len(results)}, イベント={extracted_count})"
            )

        except Exception as e:
            logger.error(f"エラー: {date_str} - {e}")
            existing_state.status = "ERROR"
            existing_state.error_message = str(e)[:500]
            existing_state.completed_at = datetime.now()
            self.stats["errors"] += 1
            self.db.commit()

    def _save_event(self, event_data: Dict[str, Any]) -> bool:
        """
        イベントをDBに保存する。
        doc_id + event_type で重複防止（冪等設計）。
        dry_run時はファイル保存のみ行う。

        Returns:
            True: 新規保存 / False: 重複スキップ or dry_run
        """
        doc_id = event_data["doc_id"]
        event_type = event_data["event_type"]
        sec_code = event_data["sec_code"]

        # 重複チェック（doc_id + event_type）
        if doc_id:
            existing = (
                self.db.query(StockEvent)
                .filter(
                    StockEvent.doc_id == doc_id,
                    StockEvent.event_type == event_type,
                )
                .first()
            )
            if existing:
                logger.debug(f"重複スキップ: doc_id={doc_id}, event_type={event_type}")
                return False

        # event_meta.json を保存（D:ドライブ）
        self._save_event_meta(event_data)

        if self.dry_run:
            logger.info(
                f"[DRY-RUN] イベント検出: {sec_code} / {event_type} / "
                f"{event_data['impact_type']} / {event_data['title'][:50]}"
            )
            return False

        # DB保存
        try:
            new_event = StockEvent(
                sec_code=sec_code,
                event_type=event_type,
                title=event_data["title"],
                doc_id=doc_id,
                source_name=event_data["source_name"],
                extraction_method=event_data["extraction_method"],
                announced_at=event_data.get("announced_at"),
            )
            self.db.add(new_event)
            self.db.flush()  # IDを取得

            # 分析データも同時保存
            analysis = StockEventAnalysis(
                event_id=new_event.id,
                impact_type=event_data["impact_type"],
                impact_strength=event_data["impact_strength"],
                summary_2lines=event_data.get("summary_2lines", ""),
            )
            self.db.add(analysis)
            self.db.commit()

            logger.info(
                f"イベント保存: id={new_event.id}, sec_code={sec_code}, "
                f"event_type={event_type}, impact={event_data['impact_type']}"
            )
            return True

        except Exception as e:
            logger.error(f"DB保存エラー: {e}")
            self.db.rollback()
            return False

    def _save_event_meta(self, event_data: Dict[str, Any]) -> None:
        """
        event_meta.json をD:ドライブに保存する。
        パス: D:\edinet_data\{YYYY}\{MM}\{doc_id}\derived\event_meta.json
        """
        doc_id = event_data.get("doc_id", "unknown")
        announced = event_data.get("announced_at")

        if announced and isinstance(announced, datetime):
            year = announced.strftime("%Y")
            month = announced.strftime("%m")
        else:
            year = datetime.now().strftime("%Y")
            month = datetime.now().strftime("%m")

        derived_dir = STORAGE_ROOT / year / month / doc_id / "derived"
        derived_dir.mkdir(parents=True, exist_ok=True)

        meta_path = derived_dir / "event_meta.json"

        # シリアライズ可能な形式に変換
        serializable = {}
        for k, v in event_data.items():
            if isinstance(v, datetime):
                serializable[k] = v.isoformat()
            else:
                serializable[k] = v

        # 既存ファイルがある場合はリスト形式でマージ
        existing_events = []
        if meta_path.exists():
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        existing_events = data
                    else:
                        existing_events = [data]
            except (json.JSONDecodeError, IOError):
                existing_events = []

        # 重複チェック（doc_id + event_type）
        is_duplicate = any(
            e.get("doc_id") == serializable.get("doc_id")
            and e.get("event_type") == serializable.get("event_type")
            for e in existing_events
        )

        if not is_duplicate:
            existing_events.append(serializable)

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(existing_events, f, ensure_ascii=False, indent=2)

        logger.debug(f"event_meta.json保存: {meta_path}")
