---
description: 変更内容に対して PM / Release Orchestrator による最終確認プロセスを実行します。
---

# PM Orchestrate Workflow

このワークフローは、現在の変更内容を PM の視点で統合的に評価し、リリース（Commit & Push）の可否を判断します。

1.  変更されたファイルと現在の git 差分を確認します。
2.  `PM_Orchestrator` スキルを適用し、指定された実行順序に従って各ゲート（Architect, UIUX, QualityGate, Regression, Security）を評価します。
3.  評価結果を指定のフォーマットで出力します。
4.  すべてのゲートが Green の場合は、レビュー結果をユーザーに報告し、commit & push の実行許可を得ます。
5.  ユーザーの承諾が得られた場合のみ、提示されたコマンドに従って commit & push を行います。
6.  NG がある場合、またはユーザーからの承認が得られない場合は、修正案を提示または作業を中断します。
