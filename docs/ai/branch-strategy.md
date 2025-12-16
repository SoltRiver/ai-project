# ブランチ運用ルール案 | Streamlit AI 株価チャートアプリ

Git運用方針と設計書生成フローのメモ。

---

## 0. 運用メモ（2025-12-09）
- v1.3 仕様対応で以下のブランチを作成済み  
  - `feature/spec-v1-3-beginner-support`（`main` から派生）
  - `review/spec-v1-3-beginner-support`（AI変更適用用・作業中）
- 作業完了後は `review` → `feature` → `main` の順でマージする

---

## 1. プロジェクト構成（例）
```
project_root/
├─ app.py                     # StreamlitメインUI
├─ data_fetcher.py            # 株価データ取得
├─ fundamental_fetcher.py     # ファンダメンタルデータ取得/評価
├─ analyzer.py                # テクニカル計算
├─ ai_client.py               # OpenAI連携
├─ docs/
│  ├─ ai/                     # AI用設計書 (.md)
│  ├─ human/                  # 人間向け設計書 (.md)
│  └─ prompts/                # AI向けプロンプト
└─ tools/
   └─ generate_docs.py        # コード→プロンプト生成
```

---

## 2. ブランチ種別
- `main` : 常に動く状態を保つ安定ブランチ。マージ後に設計書生成を実行。
- `feature/*` : 通常開発用。UI/機能追加やリファクタはここで行う。
- `exp/*` : 大規模実験・破壊的変更用。採用時は整備して feature に取り込む。
- `review/*` : AIツール適用や大規模差分の検証用。検収後に feature に戻す。

---

## 3. ライフサイクル例
1. `main` から `feature/*` を作成
2. 必要に応じて `review/*` を作成し、AI修正や大きな差分を試す
3. `review/*` → `feature/*` にマージし、確認後 `main` へマージ
4. `main` マージ後、対象モジュールの設計書生成（`docs/ai` / `docs/human`）を実行
5. 役目を終えたブランチは削除

---

## 4. 運用メモ（設計書）
- `main` 取り込み後に最新コードで設計書を再生成すること
- AI用と人間用の両方を `docs/ai` / `docs/human` に配置
