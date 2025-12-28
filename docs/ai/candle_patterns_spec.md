# ローソク足パターン仕様書（全パターン一覧）

本ファイルは、ローソク足パターンのみをまとめた仕様書です。
UI仕様は含まず、**パターン辞書としての利用**を目的とします。

---

## 共通項目
- category: 陽線 / 陰線 / 迷い
- image: SVGファイルパス
- catch: 一言キャッチ
- desc: 簡易説明（太字＋本文）
- scene: 出やすい場面
- howto: 図の見方（1行）
- notes: 注意点（箇条書き）

---

# 基本編（単体ローソク）

## 大陽線
- id: big_bull
- category: 陽線
- image: images/big_bull.svg
- catch: 買いが強い日
- desc: **買いが優勢**：実体が大きい陽線です。
- scene: 下落が続いたあと、上昇初期
- howto: 実体の大きさとヒゲの短さを見る
- notes:
  - 高値圏では勢いが弱まることがあります
  - 直前の流れと合わせて判断します

## カラカサ（ハンマー）
- id: hammer
- category: 陽線
- image: images/hammer.svg
- catch: 下で支えられた形
- desc: **下値の支持**：下ヒゲが長い足です。
- scene: 下落後の下げ止まり付近
- howto: 下ヒゲの長さと実体の位置を見る
- notes:
  - 次の足での確認が重要です

## 十字線
- id: doji
- category: 迷い
- image: images/doji.svg
- catch: 方向が決まらない
- desc: **迷いが強い**：始値と終値がほぼ同じです。
- scene: 上昇・下落の節目
- howto: 実体の小ささと前後の流れを見る
- notes:
  - 単体では方向判断はできません

---

# 応用編（複数ローソク）

## 包み足（陽）
- id: bull_engulfing
- category: 陽線
- image: images/bull_engulfing.svg
- catch: 流れが上向きに変わる
- desc: **反転の候補**：陽線が前日の足を包みます。
- scene: 下落が続いたあと
- howto: 包み方と実体の大きさを見る
- notes:
  - 上昇途中では反転にならないことがあります

## 赤三兵
- id: three_white_soldiers
- category: 陽線
- image: images/three_white_soldiers.svg
- catch: 上昇が続く
- desc: **買いが連続**：陽線が3本続きます。
- scene: 底打ち後の上昇初期
- howto: 3本の実体サイズと並びを見る
- notes:
  - 高値圏では注意が必要です

## 切り上げ三法
- id: rising_three_methods
- category: 陽線
- image: images/rising_three_methods.svg
- catch: 上昇が一服して再開
- desc: **トレンド継続**：調整後に再上昇します。
- scene: 上昇トレンド中
- howto: 最初と最後の陽線を見る
- notes:
  - レンジ相場では意味が弱まります

## 包み足（陰）
- id: bear_engulfing
- category: 陰線
- image: images/bear_engulfing.svg
- catch: 流れが下向きに変わる
- desc: **反転の候補**：陰線が前日の足を包みます。
- scene: 上昇が続いたあと
- howto: 包み方と陰線の強さを見る
- notes:
  - 下落途中では加速になる場合があります

## 黒三兵
- id: three_black_crows
- category: 陰線
- image: images/three_black_crows.svg
- catch: 下落が続く
- desc: **売りが連続**：陰線が3本続きます。
- scene: 高値圏
- howto: 3本の並びと実体サイズを見る
- notes:
  - 安値圏では反発に注意します

## 切り下げ三法
- id: falling_three_methods
- category: 陰線
- image: images/falling_three_methods.svg
- catch: 下落が一服して再開
- desc: **トレンド継続**：調整後に再下落します。
- scene: 下落トレンド中
- howto: 最初と最後の陰線を見る
- notes:
  - 上昇相場では機能しにくいです

## はらみ足
- id: harami
- category: 迷い
- image: images/harami.svg
- catch: 様子見
- desc: **迷いが増えた**：実体が内側に収まります。
- scene: 強い動きのあと
- howto: 前日の範囲に収まっているかを見る
- notes:
  - 次の足で方向を判断します

## インサイドレンジ
- id: inside_range
- category: 迷い
- image: images/inside_range.svg
- catch: 動きが小さい
- desc: **方向感なし**：値幅が縮小します。
- scene: 相場が落ち着いている場面
- howto: 値幅の縮小に注目します
- notes:
  - 頻繁に出るため過信は禁物です

## 連続十字線
- id: multiple_doji
- category: 迷い
- image: images/multiple_doji.svg
- catch: 迷いが続く
- desc: **判断待ち**：十字線が続きます。
- scene: 重要な価格帯付近
- howto: 連続性と直前の流れを見る
- notes:
  - 必ず動くわけではありません
