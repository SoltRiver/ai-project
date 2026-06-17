# LangSmith 統合ガイド

本プロジェクトでは、LLM呼び出しのトレース・評価データセット管理・プロンプト評価を
LangSmith で一元管理しています。

## 目次

1. [LangSmithでできること](#langsmithでできること)
2. [必要な環境変数](#必要な環境変数)
3. [トレースの有効化方法](#トレースの有効化方法)
4. [ニュース要約トレースの確認方法](#ニュース要約トレースの確認方法)
5. [RAGトレースの確認方法](#ragトレースの確認方法)
6. [エージェントトレースの確認方法](#エージェントトレースの確認方法)
7. [データセット作成方法](#データセット作成方法)
8. [評価スクリプト実行方法](#評価スクリプト実行方法)
9. [プロンプト変更前後の比較方法](#プロンプト変更前後の比較方法)
10. [セキュリティ注意点](#セキュリティ注意点)

---

## LangSmithでできること

- **トレース**: 全LLM呼び出し（入力・出力・実行時間・エラー）をLangSmith UIで確認
- **データセット**: 良い回答・悪い回答のサンプルをデータセットとして管理
- **評価**: プロンプト変更前後でスコアを比較し、回帰テストを実行
- **デバッグ**: エラーやレートリミットの発生状況をリアルタイムで監視

---

## 必要な環境変数

`.env.example` をコピーして `.env` に設定してください。

```env
# LangSmith トレース設定
LANGCHAIN_TRACING_V2=true        # トレース有効化
LANGSMITH_TRACING=true           # トレース有効化（新しい推奨名）
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_API_KEY=               # LangSmith APIキー
LANGCHAIN_PROJECT=stock-analysis-dev  # プロジェクト名
```

### プロジェクト名の使い分け

| プロジェクト名 | 用途 |
|---|---|
| `stock-analysis-dev` | 開発環境でのトレース |
| `stock-analysis-prod` | 本番環境でのトレース |
| `stock-analysis-rag` | RAG専用のトレース |
| `stock-analysis-agent` | エージェント専用のトレース |
| `stock-analysis-evaluation` | 評価スクリプト実行時のトレース |

---

## トレースの有効化方法

### 有効化

`.env` で以下を設定するだけで自動的にトレースが開始されます。

```env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_xxxx...
```

### 無効化

```env
LANGCHAIN_TRACING_V2=false
```

### 確認

トレースが有効かどうかは、アプリ起動時のログで確認できます:

```
LangSmith トレース有効: project=stock-analysis-dev, endpoint=https://api.smith.langchain.com, api_key=lsv2****
```

---

## ニュース要約トレースの確認方法

### トレース対象

以下の処理がLangSmithに記録されます:

1. **LangChain LCEL チェーン** (`ai/chains/news_summarizer.py`)
   - `chain.invoke()` / `chain.ainvoke()` / `chain.abatch()`
   - タグ: `news_summary`
   - メタデータ: `feature=news_summary`, `prompt_version=v1`, `model=...`

2. **LangGraph ワークフロー** (`services/langgraph/stock_news_graph.py`)
   - `graph.ainvoke()` → 各ノードが子スパンとして自動記録
   - タグ: `news_summary`, `langgraph`
   - メタデータ: `symbol=銘柄コード`, `workflow=stock_news_graph`

3. **レガシーLLM呼び出し** (`services/ai_client.py`)
   - `@traceable` デコレータで記録
   - タグ: `stock_analysis`, `news_summary`

### LangSmith UIでの確認

1. [https://smith.langchain.com](https://smith.langchain.com) にアクセス
2. プロジェクト `stock-analysis-dev` を選択
3. タグ `news_summary` でフィルタリング
4. 各トレースをクリックして詳細を確認:
   - 入力（ニュース記事）
   - プロンプト（システム・ユーザー）
   - LLMへの入力・出力
   - 要約結果
   - センチメント判定
   - 実行時間
   - エラー情報

---

## RAGトレースの確認方法

> **注意**: RAGパイプラインは現在未実装です。  
> 実装後は以下の流れがトレースされる予定です。

```
ユーザー質問 → クエリ変換 → 検索 → 取得ドキュメント → コンテキスト生成 → LLM回答生成 → 最終回答
```

タグ: `rag`

---

## エージェントトレースの確認方法

> **注意**: ツール呼び出し型の自律エージェントは現在未実装です。  
> 実装後は以下がトレースされる予定です。

- ユーザー入力 → エージェント判断 → ツール呼び出し → 中間ステップ → 最終回答
- タグ: `agent`

---

## データセット作成方法

### 1. JSONファイルの準備

`datasets/` ディレクトリに評価用データを配置:

```
datasets/
  news_summary_examples.json   # ニュース要約の良い/悪い回答例
  rag_examples.json             # RAG回答の良い/悪い回答例
  agent_examples.json           # エージェントの良い/悪い回答例
```

### 2. LangSmithへの登録

```bash
# 全データセットを登録
python scripts/create_langsmith_datasets.py

# 特定のデータセットのみ登録
python scripts/create_langsmith_datasets.py --target news_summary

# ドライラン（実際には登録しない）
python scripts/create_langsmith_datasets.py --dry-run
```

### データセット名

| 名前 | 内容 |
|---|---|
| `stock-news-summary-eval` | ニュース要約評価 |
| `stock-rag-eval` | RAG評価 |
| `stock-agent-eval` | エージェント評価 |

---

## 評価スクリプト実行方法

### 基本的な使い方

```bash
# ニュース要約の評価を実行
python scripts/run_langsmith_eval.py --target news_summary

# プロンプトバージョンを指定して評価
python scripts/run_langsmith_eval.py --target news_summary --version v2

# 全データセットの評価を実行
python scripts/run_langsmith_eval.py

# ドライラン
python scripts/run_langsmith_eval.py --dry-run
```

### 評価観点

| スコア名 | 内容 |
|---|---|
| `factuality` | 事実に基づいているか |
| `relevance` | 質問に対して適切に回答しているか |
| `clarity` | 初心者にも分かりやすいか（文字数も考慮） |
| `groundedness` | コンテキストに基づいているか（RAG向け） |
| `safety` | 投資助言になりすぎていないか |

### 結果の確認

評価結果は LangSmith UI の「Datasets & Testing」で確認できます。

---

## プロンプト変更前後の比較方法

### 手順

1. **現在のプロンプトで評価を実行**:
   ```bash
   python scripts/run_langsmith_eval.py --target news_summary --version v1
   ```

2. **プロンプトを変更**:
   - `ai/prompts/news_prompts.py` のプロンプトテンプレートを修正
   - `PROMPT_VERSION` を `"v2"` に更新

3. **変更後のプロンプトで評価を実行**:
   ```bash
   python scripts/run_langsmith_eval.py --target news_summary --version v2
   ```

4. **LangSmith UIで比較**:
   - 「Datasets & Testing」→ 対象データセットを選択
   - `news_summary-prompt-v1-*` と `news_summary-prompt-v2-*` の実行を比較
   - 各評価スコア（factuality, relevance, clarity, safety）の変化を確認

### 実行名のフォーマット

```
{target}-prompt-{version}-{timestamp}
```

例:
- `news_summary-prompt-v1-20260617-073000`
- `news_summary-prompt-v2-20260617-080000`

---

## セキュリティ注意点

### APIキーの保護

- **APIキーは `.env` にのみ記録**し、コードにハードコードしない
- `.env` は `.gitignore` に含まれており、Git管理されない
- LangSmithトレースにはAPIキーが自動的にマスキングされる

### トレースに記録されないもの

`services/langsmith_config.py` の `mask_sensitive_data()` により、
以下のパターンは自動的にマスキングされます:

- OpenAI APIキー (`sk-...`)
- Google APIキー (`AIza...`)
- LangSmith APIキー (`lsv2_...`)
- Bearer トークン
- 辞書内の `api_key`, `password`, `token`, `secret` キーの値

### 注意事項

- ニュース記事の本文はトレースに記録されます（公開情報のため問題なし）
- ユーザーの個人情報（名前、メールアドレス等）を含むデータは処理しないでください
- 本番環境では `LANGCHAIN_PROJECT=stock-analysis-prod` を設定し、
  開発トレースと分離してください
