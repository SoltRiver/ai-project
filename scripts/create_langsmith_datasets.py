"""
LangSmith データセット登録スクリプト

ローカルの datasets/*.json ファイルを読み込み、
LangSmith にデータセットを作成・更新する。

使い方:
    python scripts/create_langsmith_datasets.py

    # 特定のデータセットのみ作成
    python scripts/create_langsmith_datasets.py --target news_summary

    # ドライラン（実際には登録しない）
    python scripts/create_langsmith_datasets.py --dry-run

前提:
    - LANGCHAIN_API_KEY が環境変数または .env に設定されていること
    - datasets/ ディレクトリに JSON ファイルが存在すること
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logger = logging.getLogger(__name__)

# .envファイルから環境変数をロード
load_dotenv()

# ====================================================================
# データセット定義
# JSONファイル名とLangSmithデータセット名のマッピング
# ====================================================================

DATASET_CONFIGS: Dict[str, Dict[str, str]] = {
    "news_summary": {
        "file": "datasets/news_summary_examples.json",
        "dataset_name": "stock-news-summary-eval",
        "description": (
            "株式ニュース要約の評価用データセット。"
            "良い要約（事実に基づく、初心者向け）と"
            "悪い要約（投資助言、曖昧）のサンプルを含む。"
        ),
    },
    "rag": {
        "file": "datasets/rag_examples.json",
        "dataset_name": "stock-rag-eval",
        "description": (
            "RAG検索・回答の評価用データセット。"
            "コンテキストに基づく正確な回答と"
            "コンテキスト外の情報を捏造した回答のサンプルを含む。"
        ),
    },
    "agent": {
        "file": "datasets/agent_examples.json",
        "dataset_name": "stock-agent-eval",
        "description": (
            "AIエージェントのツール選択・回答品質の評価用データセット。"
            "適切なツール選択と過剰なツール呼び出しのサンプルを含む。"
        ),
    },
}


def load_examples(file_path: str) -> List[Dict[str, Any]]:
    """
    JSONファイルから評価用サンプルを読み込む。

    Args:
        file_path: JSONファイルのパス

    Returns:
        サンプルのリスト

    Raises:
        FileNotFoundError: ファイルが見つからない場合
        json.JSONDecodeError: JSON解析エラーの場合
    """
    abs_path = Path(file_path)
    if not abs_path.is_absolute():
        # プロジェクトルートからの相対パス
        abs_path = Path(__file__).resolve().parent.parent / file_path

    if not abs_path.exists():
        raise FileNotFoundError(f"データセットファイルが見つかりません: {abs_path}")

    with open(abs_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"JSONファイルはリスト形式である必要があります: {abs_path}")

    logger.info(f"  ファイル読み込み完了: {abs_path} ({len(data)}件)")
    return data


def create_or_update_dataset(
    client: Any,
    dataset_name: str,
    description: str,
    examples: List[Dict[str, Any]],
    dry_run: bool = False,
) -> None:
    """
    LangSmithにデータセットを作成し、サンプルを登録する。

    既存のデータセットがある場合は、新規サンプルのみ追加する。
    （既存サンプルとの重複は入力値のハッシュで判定）

    Args:
        client: LangSmith クライアント
        dataset_name: データセット名
        description: データセットの説明
        examples: サンプルのリスト
        dry_run: Trueの場合は実際に登録しない
    """
    if dry_run:
        logger.info(
            f"  [DRY RUN] データセット '{dataset_name}' に "
            f"{len(examples)}件を登録予定"
        )
        for i, ex in enumerate(examples):
            label = ex.get("metadata", {}).get("label", "-")
            logger.info(
                f"    [{i}] label={label}, inputs={list(ex.get('inputs', {}).keys())}"
            )
        return

    # データセットの作成または取得
    try:
        dataset = client.read_dataset(dataset_name=dataset_name)
        logger.info(f"  既存データセット '{dataset_name}' を使用")
    except Exception:
        dataset = client.create_dataset(
            dataset_name=dataset_name,
            description=description,
        )
        logger.info(f"  新規データセット '{dataset_name}' を作成")

    # 既存のサンプル数を取得（重複チェック用）
    try:
        existing_examples = list(client.list_examples(dataset_id=dataset.id))
        existing_count = len(existing_examples)
        logger.info(f"  既存サンプル数: {existing_count}件")
    except Exception:
        existing_count = 0

    # サンプルの登録
    added_count = 0
    for ex in examples:
        inputs = ex.get("inputs", {})
        outputs = ex.get("outputs", {})
        metadata = ex.get("metadata", {})

        # 重複チェック: 同じ入力データが既に登録されているかを簡易判定
        # （完全な重複排除はLangSmith側で行う）
        input_str = json.dumps(inputs, sort_keys=True, ensure_ascii=False)
        is_duplicate = False
        for existing in existing_examples if existing_count > 0 else []:
            existing_input_str = json.dumps(
                existing.inputs, sort_keys=True, ensure_ascii=False
            )
            if input_str == existing_input_str:
                is_duplicate = True
                break

        if is_duplicate:
            logger.info(f"    スキップ（重複）: " f"{list(inputs.keys())}")
            continue

        client.create_example(
            inputs=inputs,
            outputs=outputs,
            metadata=metadata,
            dataset_id=dataset.id,
        )
        added_count += 1

    logger.info(
        f"  登録完了: 新規={added_count}件, "
        f"スキップ={len(examples) - added_count}件"
    )


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="LangSmith にデータセットを登録する")
    parser.add_argument(
        "--target",
        choices=list(DATASET_CONFIGS.keys()),
        help="特定のデータセットのみ作成（省略時は全て）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="実際に登録せず、処理内容を表示のみ",
    )
    args = parser.parse_args()

    # ロギング設定
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    # LangSmith API キーの確認
    api_key = os.getenv("LANGCHAIN_API_KEY")
    if not api_key and not args.dry_run:
        logger.error(
            "LANGCHAIN_API_KEY が設定されていません。"
            ".env ファイルまたは環境変数に設定してください。"
        )
        sys.exit(1)

    # LangSmith クライアント初期化
    if not args.dry_run:
        from langsmith import Client

        client = Client()
        logger.info("LangSmith クライアント初期化完了")
    else:
        client = None
        logger.info("[DRY RUN モード] 実際の登録は行いません")

    # 対象データセットの決定
    targets = (
        {args.target: DATASET_CONFIGS[args.target]} if args.target else DATASET_CONFIGS
    )

    # 各データセットを処理
    for target_key, config in targets.items():
        logger.info(f"\n{'=' * 60}")
        logger.info(f"データセット: {target_key}")
        logger.info(f"{'=' * 60}")

        try:
            # JSONファイル読み込み
            examples = load_examples(config["file"])

            # データセット作成・更新
            create_or_update_dataset(
                client=client,
                dataset_name=config["dataset_name"],
                description=config["description"],
                examples=examples,
                dry_run=args.dry_run,
            )

        except FileNotFoundError as e:
            logger.error(f"  エラー: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"  JSON解析エラー: {e}")
        except Exception as e:
            logger.error(f"  予期しないエラー: {type(e).__name__}: {e}")

    logger.info("\n全データセットの処理が完了しました。")


if __name__ == "__main__":
    main()
