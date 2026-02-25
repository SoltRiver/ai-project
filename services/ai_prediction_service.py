import pandas as pd
import numpy as np
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import lightgbm as lgb
from sklearn.metrics import brier_score_loss
from sklearn.model_selection import TimeSeriesSplit

from services.market_service import fetch_market_indicators, get_market_features
from services.news_service import get_news_tendency
from services.margin_service import get_margin_tab

logger = logging.getLogger(__name__)

class AIPredictor:
    """
    利確先着確率（AI）を算出するための予測サービス (v1.1)
    """
    def __init__(self, target_days: int = 20, r_multiplier: float = 1.0, cost_r: float = 0.02):
        self.target_days = target_days
        self.r_multiplier = r_multiplier
        self.cost_r = cost_r
        self.model = None
        self.validation_results = {
            "brier_score": "-",
            "n": 0,
            "period": "-"
        }

    def engineer_features(self, df: pd.DataFrame, code: str = None) -> pd.DataFrame:
        """
        特徴量エンジニアリング (v1.1)
        チャート、市場動向、ニュースを考慮する。
        """
        if df is None or len(df) < 75:
            return pd.DataFrame()

        feat = pd.DataFrame(index=df.index)
        
        # 終値ベース
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df['volume']

        # 1. チャート特徴量
        sma25 = close.rolling(window=25).mean()
        sma75 = close.rolling(window=75).mean()
        feat['sma_divergence'] = (sma25 - sma75) / sma75
        feat['sma75_slope'] = sma75.diff(10) / sma75.shift(10)
        
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        feat['rsi14'] = 100 - (100 / (1 + rs))

        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr14 = tr.rolling(window=14).mean()
        feat['atr_ratio'] = atr14 / close
        feat['volume_ratio'] = volume.rolling(window=5).mean() / volume.rolling(window=60).mean()
        feat['return_1d'] = close.pct_change(1)
        feat['return_5d'] = close.pct_change(5)
        feat['volatility_20'] = close.pct_change().rolling(window=20).std()

        # 2. 市場動向特徴量 (TOPIX, N225)
        feat['topix_ret_1d'] = 0.0
        feat['topix_ret_5d'] = 0.0
        feat['n225_ret_1d'] = 0.0
        feat['n225_ret_5d'] = 0.0

        # 3. ニュース傾向特徴量
        feat['news_pos_7d'] = 0.0
        feat['news_neg_7d'] = 0.0

        return feat.dropna()

    def label_data(self, df: pd.DataFrame) -> pd.Series:
        """
        教師データの作成 (v1同様)
        """
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
            
            for _, row in target_window.iterrows():
                if row['high'] >= tp_price:
                    hit_tp = True
                    break
                if row['low'] <= sl_price:
                    hit_sl = True
                    break
            
            if hit_tp:
                labels.append(1)
            else:
                labels.append(0)
                
        return pd.Series(labels, index=df.index)

    def train_and_validate(self, df: pd.DataFrame):
        """
        時系列分割(Walk-forward)で学習と検証を行う
        """
        features = self.engineer_features(df)
        labels = self.label_data(df)
        
        data = features.join(labels.rename('target')).dropna()
        if len(data) < 300:
            logger.warning("Data too small for validation")
            return
        
        X = data.drop(columns=['target'])
        y = data['target']
        
        tscv = TimeSeriesSplit(n_splits=5)
        scores = []
        
        params = {
            'n_estimators': 100,
            'learning_rate': 0.05,
            'num_leaves': 15,
            'random_state': 42,
            'verbose': -1,
            'min_child_samples': 20
        }

        for train_index, test_index in tscv.split(X):
            X_train, X_test = X.iloc[train_index], X.iloc[test_index]
            y_train, y_test = y.iloc[train_index], y.iloc[test_index]
            
            model = lgb.LGBMClassifier(**params)
            model.fit(X_train, y_train)
            
            probs = model.predict_proba(X_test)[:, 1]
            score = brier_score_loss(y_test, probs)
            scores.append(score)
            
        self.model = lgb.LGBMClassifier(**params).fit(X, y)
        
        self.validation_results = {
            "brier_score": round(np.mean(scores), 4) if scores else "-",
            "n": len(data),
            "period": f"{data.index[0].strftime('%Y-%m-%d')}〜{data.index[-1].strftime('%Y-%m-%d')}"
        }

    def predict_latest(self, df: pd.DataFrame, code: str) -> Dict[str, Any]:
        """
        最新の足に対する予測値、期待値、矛盾チェックを返す (v1.1)
        """
        if code is None:
             return {"error": "銘柄コードが指定されていません"}

        if self.model is None:
            try:
                self.train_and_validate(df)
            except Exception as e:
                logger.error(f"Training failed: {e}")
            
        if self.model is None:
            return {
                "probability": "-", 
                "expected_return": "-",
                "is_provisional": False,
                "validation": self.validation_results,
                "attention": None
            }

        features = self.engineer_features(df, code)
        if features.empty:
            return {
                "probability": "-", 
                "expected_return": "-",
                "is_provisional": False,
                "validation": self.validation_results,
                "attention": None
            }
            
        latest_idx = features.index[-1]
        latest_features = features.iloc[[-1]].copy()

        # 市場動向とニュース傾向を最新データで更新
        news_summary = ""
        try:
            market_dfs = fetch_market_indicators()
            market_feats = get_market_features(market_dfs, latest_idx)
            latest_features['topix_ret_1d'] = market_feats.get('TOPIX_ret_1d', 0.0)
            latest_features['topix_ret_5d'] = market_feats.get('TOPIX_ret_5d', 0.0)
            latest_features['n225_ret_1d'] = market_feats.get('N225_ret_1d', 0.0)
            latest_features['n225_ret_5d'] = market_feats.get('N225_ret_5d', 0.0)
            
            news_tendency = get_news_tendency(code)
            latest_features['news_pos_7d'] = news_tendency['counts']['last_7d']['pos']
            latest_features['news_neg_7d'] = news_tendency['counts']['last_7d']['neg']
            news_summary = news_tendency.get("summary_text", "")
        except Exception as e:
            logger.error(f"Feature update failed for {code}: {e}")

        prob = self.model.predict_proba(latest_features)[0, 1]
        
        # 期待値計算 E_R = (2p - 1) - cR
        expected_return = (2 * prob - 1) - self.cost_r
        
        # 未確定足の判定 (最新日付は常に未確定)
        is_provisional = False
        latest_date = df.index[-1]
        
        # pandas.Timestamp を datetime.date に変換
        if hasattr(latest_date, 'date'):
            latest_date_val = latest_date.date()
        elif isinstance(latest_date, datetime):
            latest_date_val = latest_date.date()
        else:
            try:
                latest_date_val = pd.to_datetime(latest_date).date()
            except:
                latest_date_val = latest_date

        if isinstance(latest_date_val, (datetime, pd.Timestamp)):
             latest_date_val = latest_date_val.date()

        if latest_date_val >= datetime.now().date():
            is_provisional = True
            
        # 信頼度評価の取得（矛盾チェック用）
        attention = None
        try:
            margin_tab = get_margin_tab(code)
            reliability_label = margin_tab.get("margin", {}).get("reliability_label", "未確定")
            
            # 矛盾(注意)チェック
            if reliability_label == "高" and expected_return < 0:
                attention = "注意：AI期待値がマイナス（E_R<0）"
            elif reliability_label == "低" and expected_return > 0.20:
                attention = "注意：AI期待値が高め（E_R>+0.20）"
        except Exception as e:
            logger.error(f"Consistency check failed: {e}")

        return {
            "probability": round(float(prob), 2),
            "expected_return": round(float(expected_return), 2),
            "is_provisional": is_provisional,
            "validation": self.validation_results,
            "attention": attention,
            "news_summary": news_summary
        }

# シングルトン的利用
predictor = AIPredictor()
