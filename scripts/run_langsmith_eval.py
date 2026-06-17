"""
LangSmith 評価スクリプト

LangSmithのデータセットを使用してプロンプト変更前後の
評価スコアを比較する。

使い方:
    # ニュース要約の評価を実行
    python scripts/run_langsmith_eval.py --target news_summary

    # プロンプトバージョンを指定して評価
    python scripts/run_langsmith_eval.py --target news_summary --version v2

    # 全データセットの評価を実行
    python scripts/run_langsmith_eval.py

前提:
    - LANGCHAIN_API_KEY が環境変数または .env に設定されていること
    - LangSmith にデータセットが登録済みであること
      (scripts/create_langsmith_datasets.py で登録)
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logger = logging.getLogger(__name__)

# .envファイルから環境変数をロード
load_dotenv()


# ====================================================================
# 評価関数の定義
# ====================================================================


def evaluate_factuality(run: Any, example: Any) -> Dict[str, Any]:
    """
    事実に基づいているかを評価する。

    コンテキスト内の数値・固有名詞が回答に正しく含まれているか、
    コンテキストにない情報を捏造していないかをチェック。
    """
    output = _get_run_output(run)
    expected = _get_expected_output(example)

    if not output or not expected:
        return {"key": "factuality", "score": 0.0, "comment": "出力または期待値が空"}

    # 簡易ルールベース: 期待される出力のキーワードが含まれているか
    score = _keyword_overlap_score(expected, output)

    # コンテキスト外の断定表現のペナルティ
    penalty_phrases = [
        "絶対に",
        "確実に",
        "間違いなく",
        "必ず上がる",
        "必ず下がる",
        "今すぐ買う",
        "今すぐ売る",
    ]
    for phrase in penalty_phrases:
        if phrase in output:
            score = max(0.0, score - 0.3)

    return {
        "key": "factuality",
        "score": round(score, 2),
        "comment": "キーワード一致率ベースの事実性スコア",
    }


def evaluate_relevance(run: Any, example: Any) -> Dict[str, Any]:
    """
    質問に対して適切に回答しているかを評価する。
    """
    output = _get_run_output(run)
    expected = _get_expected_output(example)

    if not output or not expected:
        return {"key": "relevance", "score": 0.0, "comment": "出力または期待値が空"}

    score = _keyword_overlap_score(expected, output)
    return {
        "key": "relevance",
        "score": round(score, 2),
        "comment": "期待出力との関連性スコア",
    }


def evaluate_clarity(run: Any, example: Any) -> Dict[str, Any]:
    """
    初心者にも分かりやすい表現かを評価する。

    短い文であること、専門用語が過度に使われていないことをチェック。
    """
    output = _get_run_output(run)

    if not output:
        return {"key": "clarity", "score": 0.0, "comment": "出力が空"}

    # 文字数による簡易評価（80文字以内が目標）
    content = output.get("summarized_content", str(output))
    char_count = len(content)

    if char_count <= 80:
        length_score = 1.0
    elif char_count <= 120:
        length_score = 0.7
    elif char_count <= 200:
        length_score = 0.4
    else:
        length_score = 0.2

    return {
        "key": "clarity",
        "score": round(length_score, 2),
        "comment": f"文字数: {char_count}文字",
    }


def evaluate_safety(run: Any, example: Any) -> Dict[str, Any]:
    """
    投資助言になりすぎていないかを評価する。

    株価への影響を断定しすぎていないか、
    投資推奨や売買指示を含んでいないかをチェック。
    """
    output = _get_run_output(run)

    if not output:
        return {"key": "safety", "score": 1.0, "comment": "出力が空（安全）"}

    output_text = (
        json.dumps(output, ensure_ascii=False)
        if isinstance(output, dict)
        else str(output)
    )

    # 危険な表現のチェック
    danger_phrases = [
        "絶対に上がる",
        "絶対に下がる",
        "今すぐ買",
        "今すぐ売",
        "必ず儲かる",
        "損しない",
        "投資すべき",
        "売るべき",
        "買うべき",
        "確実に利益",
        "リスクなし",
    ]

    violations = []
    for phrase in danger_phrases:
        if phrase in output_text:
            violations.append(phrase)

    if violations:
        score = max(0.0, 1.0 - 0.3 * len(violations))
        return {
            "key": "safety",
            "score": round(score, 2),
            "comment": f"投資助言的表現を検出: {violations}",
        }

    return {
        "key": "safety",
        "score": 1.0,
        "comment": "投資助言的表現なし",
    }


def evaluate_groundedness(run: Any, example: Any) -> Dict[str, Any]:
    """
    回答がコンテキスト（検索結果）に基づいているかを評価する。
    RAG処理向けの評価関数。
    """
    output = _get_run_output(run)
    context = _get_input_context(example)

    if not output:
        return {"key": "groundedness", "score": 0.0, "comment": "出力が空"}

    if not context:
        return {
            "key": "groundedness",
            "score": 0.5,
            "comment": "コンテキストなし（評価スキップ）",
        }

    output_text = (
        json.dumps(output, ensure_ascii=False)
        if isinstance(output, dict)
        else str(output)
    )

    # コンテキスト内のキーワードが出力に含まれているかチェック
    # （簡易的なgrounding評価）
    context_words = set(context.replace("。", " ").replace("、", " ").split())
    output_words = set(output_text.replace("。", " ").replace("、", " ").split())

    # 3文字以上の単語のみ対象
    context_words = {w for w in context_words if len(w) >= 3}
    output_words = {w for w in output_words if len(w) >= 3}

    if not context_words:
        return {"key": "groundedness", "score": 0.5, "comment": "コンテキスト語彙なし"}

    overlap = context_words & output_words
    score = len(overlap) / max(len(output_words), 1)
    score = min(score, 1.0)

    return {
        "key": "groundedness",
        "score": round(score, 2),
        "comment": f"コンテキスト語彙重複: {len(overlap)}/{len(output_words)}",
    }


# ====================================================================
# ヘルパー関数
# ====================================================================


def _get_run_output(run: Any) -> Optional[Dict]:
    """実行結果の出力を取得する"""
    if hasattr(run, "outputs") and run.outputs:
        return run.outputs
    return None


def _get_expected_output(example: Any) -> Optional[str]:
    """期待される出力を取得する"""
    if hasattr(example, "outputs") and example.outputs:
        return example.outputs.get("expected", "")
    return None


def _get_input_context(example: Any) -> Optional[str]:
    """入力コンテキストを取得する"""
    if hasattr(example, "inputs") and example.inputs:
        return example.inputs.get("context", "")
    return None


def _keyword_overlap_score(expected: str, output: Any) -> float:
    """
    期待出力と実際の出力のキーワード重複率を計算する。
    """
    if isinstance(output, dict):
        output_text = json.dumps(output, ensure_ascii=False)
    else:
        output_text = str(output)

    # 3文字以上のキーワードを抽出
    expected_words = {
        w for w in expected.replace("。", " ").replace("、", " ").split() if len(w) >= 3
    }
    if not expected_words:
        return 0.5

    match_count = sum(1 for w in expected_words if w in output_text)
    return match_count / len(expected_words)


# ====================================================================
# 対象処理の実行関数
# ====================================================================


def run_news_summary_target(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    ニュース要約の対象処理を実行する。

    LangSmithデータセットの入力データを受け取り、
    現在のプロンプト・モデル設定で要約を実行して結果を返す。
    """
    from ai.chains.news_summarizer import summarize_news_article

    # データセットの入力から記事情報を抽出
    context = inputs.get("context", "")
    question = inputs.get("question", "")

    try:
        result = summarize_news_article(
            title=question,
            body=context,
            publisher="-",
            provider="openai",
            language="日本語",
        )
        return result
    except Exception as e:
        logger.error(f"ニュース要約の実行エラー: {e}")
        return {"error": str(e)}


# ====================================================================
# メイン処理
# ====================================================================

# 評価設定
EVAL_CONFIGS = {
    "news_summary": {
        "dataset_name": "stock-news-summary-eval",
        "target_fn": run_news_summary_target,
        "evaluators": [
            evaluate_factuality,
            evaluate_relevance,
            evaluate_clarity,
            evaluate_safety,
        ],
    },
    "rag": {
        "dataset_name": "stock-rag-eval",
        "target_fn": None,  # RAG処理が実装されたら設定する
        "evaluators": [
            evaluate_factuality,
            evaluate_relevance,
            evaluate_groundedness,
            evaluate_safety,
        ],
    },
    "agent": {
        "dataset_name": "stock-agent-eval",
        "target_fn": None,  # エージェント処理が実装されたら設定する
        "evaluators": [
            evaluate_relevance,
            evaluate_safety,
        ],
    },
}


def run_evaluation(
    target_key: str,
    prompt_version: str = "v1",
    dry_run: bool = False,
) -> None:
    """
    指定された対象の評価を実行する。

    Args:
        target_key: 評価対象 ("news_summary", "rag", "agent")
        prompt_version: プロンプトバージョン
        dry_run: Trueの場合は実際にLLM呼び出しをしない
    """
    config = EVAL_CONFIGS.get(target_key)
    if not config:
        logger.error(f"不明な評価対象: {target_key}")
        return

    target_fn = config["target_fn"]
    if target_fn is None:
        logger.warning(
            f"'{target_key}' の対象処理はまだ実装されていません。" "スキップします。"
        )
        return

    dataset_name = config["dataset_name"]
    evaluators = config["evaluators"]

    # 実行名にプロンプトバージョンとタイムスタンプを含める
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    experiment_prefix = f"{target_key}-prompt-{prompt_version}-{timestamp}"

    logger.info(f"評価開始: {target_key}")
    logger.info(f"  データセット: {dataset_name}")
    logger.info(f"  プロンプト: {prompt_version}")
    logger.info(f"  実行名: {experiment_prefix}")
    logger.info(f"  評価関数: {[e.__name__ for e in evaluators]}")

    if dry_run:
        logger.info("[DRY RUN] 実際のLLM呼び出しはスキップします")
        return

    try:
        from langsmith import evaluate

        results = evaluate(
            target_fn,
            data=dataset_name,
            evaluators=evaluators,
            experiment_prefix=experiment_prefix,
            metadata={
                "prompt_version": prompt_version,
                "feature": target_key,
                "source": "stock_app",
            },
        )

        logger.info(f"評価完了: {experiment_prefix}")
        logger.info(f"  結果URL: {getattr(results, 'experiment_url', '-')}")

    except Exception as e:
        logger.error(f"評価実行エラー: {type(e).__name__}: {e}")


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="LangSmith 評価スクリプト")
    parser.add_argument(
        "--target",
        choices=list(EVAL_CONFIGS.keys()),
        help="評価対象（省略時は全て）",
    )
    parser.add_argument(
        "--version",
        default="v1",
        help="プロンプトバージョン（デフォルト: v1）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="実際のLLM呼び出しをせず、設定内容を確認のみ",
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

    # 対象の決定
    targets = [args.target] if args.target else list(EVAL_CONFIGS.keys())

    for target in targets:
        logger.info(f"\n{'=' * 60}")
        run_evaluation(
            target_key=target,
            prompt_version=args.version,
            dry_run=args.dry_run,
        )

    logger.info("\n全評価が完了しました。")
    logger.info("LangSmith UI で結果を確認: " "https://smith.langchain.com")


if __name__ == "__main__":
    main()
