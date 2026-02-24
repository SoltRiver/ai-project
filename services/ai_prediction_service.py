import pandas as pd
import numpy as np
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import lightgbm as lgb
from sklearn.metrics import brier_score_loss
from sklearn.model_selection import TimeSeriesSplit

logger = logging.getLogger(__name__)

class AIPredictor:
    """
    利確先着確率（AI）を算出するための予測サービス (v1)
    """
    def __init__(self, target_days: int = 20, r_multiplier: float = 1.0):
        self.target_days = target_days
        self.r_multiplier = r_multiplier
        self.model = None
        self.validation_results = {
            "brier_score": "-",
            "n": 0,
            "period": "-"
        }

    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        特徴量エンジニアリング (v1固定)
        将来データを含めないように注意
        """
        if df is None or len(df) < 75:
            return pd.DataFrame()

        feat = pd.DataFrame(index=df.index)
        
        # 終値ベース
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df['volume']

        # 1. MA25とMA75の乖離率
        sma25 = close.rolling(window=25).mean()
        sma75 = close.rolling(window=75).mean()
        feat['sma_divergence'] = (sma25 - sma75) / sma75

        # 2. MA75の傾き（直近10日差分）
        feat['sma75_slope'] = sma75.diff(10) / sma75.shift(10)

        # 3. RSI(14)
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        feat['rsi14'] = 100 - (100 / (1 + rs))

        # 4. ATR(14) / 終値
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr14 = tr.rolling(window=14).mean()
        feat['atr_ratio'] = atr14 / close

        # 5. 出来高比（直近5日 vs 60日平均）
        vol5 = volume.rolling(window=5).mean()
        vol60 = volume.rolling(window=60).mean()
        feat['volume_ratio'] = vol5 / vol60

        # 6. 直近1日/5日リターン
        feat['return_1d'] = close.pct_change(1)
        feat['return_5d'] = close.pct_change(5)

        # 7. ボラティリティ指標 (直近20日)
        feat['volatility_20'] = close.pct_change().rolling(window=20).std()

        return feat.dropna()

    def label_data(self, df: pd.DataFrame) -> pd.Series:
        """
        教師データの作成
        次の20営業日以内に利確(+1R)に先に到達するか
        R = ATR(14) を暫定的に使用（シナリオ定義に合わせる必要あり）
        """
        # v1では R=1固定（リスク幅を1とするが、実際には価格変動率などに基づくべき）
        # 要件「Rは1固定」は「利確ライン(+1R)」「損切りライン(-1R)」のRを指すと解釈。
        # ここでは ATR(14) をリスク幅 1R と定義して検証する。
        
        tr1 = df['high'] - df['low']
        tr2 = abs(df['high'] - df['close'].shift(1))
        tr3 = abs(df['low'] - df['close'].shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr14 = tr.rolling(window=14).mean()
        
        labels = []
        for i in range(len(df)):
            if i + self.target_days >= len(df):
                labels.append(np.nan)
                continue
            
            start_price = df['close'].iloc[i]
            risk_amount = atr14.iloc[i] * self.r_multiplier
            
            tp_price = start_price + risk_amount
            sl_price = start_price - risk_amount
            
            target_window = df.iloc[i+1 : i+1+self.target_days]
            
            hit_tp = False
            hit_sl = False
            
            # 実際には high/low で細かく判定
            for _, row in target_window.iterrows():
                if row['high'] >= tp_price:
                    hit_tp = True
                    break
                if row['low'] <= sl_price:
                    hit_sl = True
                    break
            
            if hit_tp:
                labels.append(1)
            elif hit_sl:
                labels.append(0)
            else:
                # 20日以内にどちらにも到達しない場合
                # v1では利確に到達しなかったものとして0（または除外するが、バイアスを避けるため0とするのが一般的）
                # ただし「利確が先に到達する確率」なので、到達しなければ0。
                labels.append(0)
                
        return pd.Series(labels, index=df.index)

    def train_and_validate(self, df: pd.DataFrame):
        """
        時系列分割(Walk-forward)で学習と検証を行う
        全銘柄統合学習を想定するが、まずは単一銘柄または小規模セットで実装
        """
        features = self.engineer_features(df)
        labels = self.label_data(df)
        
        data = features.join(labels.rename('target')).dropna()
        if len(data) < 300:
            logger.warning("Data too small for validation")
            return
        
        X = data.drop(columns=['target'])
        y = data['target']
        
        # 時系列分割
        tscv = TimeSeriesSplit(n_splits=5)
        scores = []
        
        for train_index, test_index in tscv.split(X):
            X_train, X_test = X.iloc[train_index], X.iloc[test_index]
            y_train, y_test = y.iloc[train_index], y.iloc[test_index]
            
            model = lgb.LGBMClassifier(
                n_estimators=100,
                learning_rate=0.05,
                num_leaves=31,
                random_state=42,
                verbose=-1
            )
            model.fit(X_train, y_train)
            
            probs = model.predict_proba(X_test)[:, 1]
            score = brier_score_loss(y_test, probs)
            scores.append(score)
            
        # 最終モデルを全データで学習（または最新期間を除く）
        self.model = lgb.LGBMClassifier(
            n_estimators=100,
            learning_rate=0.05,
            num_leaves=31,
            random_state=42,
            verbose=-1
        ).fit(X, y)
        
        self.validation_results = {
            "brier_score": round(np.mean(scores), 4) if scores else "-",
            "n": len(data),
            "period": f"{data.index[0].strftime('%Y-%m-%d')}〜{data.index[-1].strftime('%Y-%m-%d')}"
        }

    def predict_latest(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        最新の足に対する予測値を返す
        """
        if self.model is None:
            # 本来はキャッシュからロードするか、全銘柄で事前学習しておく
            try:
                self.train_and_validate(df)
            except Exception as e:
                logger.error(f"Training failed: {e}")
            
        if self.model is None:
            return {
                "probability": "-", 
                "is_provisional": False,
                "validation": self.validation_results
            }

        features = self.engineer_features(df)
        if features.empty:
            return {
                "probability": "-", 
                "is_provisional": False,
                "validation": self.validation_results
            }
            
        latest_features = features.iloc[[-1]]
        prob = self.model.predict_proba(latest_features)[0, 1]
        
        # 未確定足の判定
        is_provisional = False
        latest_date = df.index[-1]
        if hasattr(latest_date, 'date'):
            latest_date = latest_date.date()
        
        # 簡易判定：最新の足が今日の足なら暫定
        if latest_date >= datetime.now().date():
            is_provisional = True
            
        return {
            "probability": round(float(prob), 2),
            "is_provisional": is_provisional,
            "validation": self.validation_results
        }

# シングルトン的利用
predictor = AIPredictor()
