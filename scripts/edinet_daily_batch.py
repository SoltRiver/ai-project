"""
EDINET 日次バッチ — CLIエントリーポイント

毎日実行して銘柄情報を自動取得する。
1日100リクエストのバジェット内で動作する。

使用方法:
    # 基本実行（今日の日付）
    python scripts/edinet_daily_batch.py

    # 日付指定
    python scripts/edinet_daily_batch.py --date 2026-04-19

    # ドライラン（APIコールなし、動作確認用）
    python scripts/edinet_daily_batch.py --dry-run

    # バジェット上限変更
    python scripts/edinet_daily_batch.py --budget 50

    # 組み合わせ
    python scripts/edinet_daily_batch.py --date 2026-04-19 --budget 30 --dry-run
"""

import sys
import os
import argparse
import logging
from datetime import datetime, date

# プロジェクトルートをパスに追加
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv

load_dotenv()

# ロガー設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            os.path.join(PROJECT_ROOT, "edinet_batch.log"), encoding="utf-8"
        ),
    ],
)
logger = logging.getLogger("edinet_daily_batch")


def main():
    parser = argparse.ArgumentParser(
        description="EDINET 日次バッチ — 銘柄情報の自動取得（100リクエスト/日）"
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="対象日付（YYYY-MM-DD形式）。省略時は今日。",
    )
    parser.add_argument(
        "--budget",
        type=int,
        default=None,
        help="APIリクエスト上限の上書き（デフォルト: 設定ファイルの値）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="ドライラン: APIコールを行わず、処理フローのみ確認",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="設定ファイルパス（省略時: config/edinet_batch_config.yml）",
    )

    args = parser.parse_args()

    # 日付パース
    if args.date:
        try:
            target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            print(f"ERROR: 日付形式が不正です: {args.date}（YYYY-MM-DD形式で指定）")
            sys.exit(1)
    else:
        target_date = date.today()

    # EDINET_API_KEY チェック
    api_key = os.environ.get("EDINET_API_KEY")
    if not api_key and not args.dry_run:
        print("ERROR: EDINET_API_KEY が設定されていません。")
        print("  .env ファイルに EDINET_API_KEY=xxxxx を設定してください。")
        sys.exit(1)

    # テーブル初期化（初回のみ）
    from database import engine, Base
    from models.edinet_batch_log import EdinetBatchLog
    from models.edinet_document import EdinetDocument
    from models.edinet_file import EdinetFile
    from models.company_info import CompanyInfo
    from models.master import StockMaster

    Base.metadata.create_all(bind=engine)

    # バッチサービス起動
    from services.edinet_daily_batch_service import EdinetDailyBatchService

    service = EdinetDailyBatchService(
        dry_run=args.dry_run,
        budget_override=args.budget,
        config_path=args.config,
    )

    service.run(target_date)


if __name__ == "__main__":
    main()
