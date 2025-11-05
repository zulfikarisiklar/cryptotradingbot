"""
Machine Learning Engine for cryptocurrency trading.
Uses multiple ML models to learn patterns and make predictions.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import logging
import pickle
import os

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import xgboost as xgb
import lightgbm as lgb

from src.indicators.technical_indicators import TechnicalIndicators
from src.sentiment.sentiment_analyzer import SentimentAnalyzer, VolumeAnalyzer
from src.config import config

logger = logging.getLogger(__name__)


class MLEngine:
    """
    Machine Learning engine for trading predictions.
    Combines technical indicators, sentiment, and volume analysis.
    """

    def __init__(self, model_dir: str = 'models'):
        """
        Initialize ML engine.

        Args:
            model_dir: Directory to save/load models
        """
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)

        # Initialize models
        self.models = {
            'random_forest': RandomForestClassifier(
                n_estimators=200,
                max_depth=10,
                min_samples_split=5,
                random_state=42
            ),
            'xgboost': xgb.XGBClassifier(
                n_estimators=200,
                max_depth=8,
                learning_rate=0.1,
                random_state=42
            ),
            'lightgbm': lgb.LGBMClassifier(
                n_estimators=200,
                max_depth=8,
                learning_rate=0.1,
                random_state=42
            ),
            'gradient_boosting': GradientBoostingClassifier(
                n_estimators=200,
                max_depth=8,
                learning_rate=0.1,
                random_state=42
            )
        }

        self.scaler = StandardScaler()
        self.feature_columns = []
        self.trained = False

        logger.info("MLEngine initialized")

    def prepare_features(self, df: pd.DataFrame,
                        include_sentiment: bool = True,
                        symbol: Optional[str] = None) -> pd.DataFrame:
        """
        Prepare features for machine learning.

        Args:
            df: DataFrame with OHLCV data
            include_sentiment: Whether to include sentiment features
            symbol: Symbol for sentiment analysis

        Returns:
            DataFrame with all features
        """
        logger.info("Preparing features for ML...")

        # Calculate technical indicators
        tech_indicators = TechnicalIndicators(df)
        features_df = tech_indicators.calculate_all_indicators()

        # Add volume features
        volume_features = VolumeAnalyzer.calculate_volume_features(df)
        features_df = pd.concat([features_df, volume_features], axis=1)

        # Add price-based features
        features_df['returns_1'] = df['close'].pct_change(1)
        features_df['returns_5'] = df['close'].pct_change(5)
        features_df['returns_10'] = df['close'].pct_change(10)
        features_df['returns_20'] = df['close'].pct_change(20)

        # Price momentum
        features_df['momentum_5'] = df['close'] / df['close'].shift(5) - 1
        features_df['momentum_10'] = df['close'] / df['close'].shift(10) - 1

        # High/Low ratios
        features_df['high_low_ratio'] = df['high'] / df['low']
        features_df['close_open_ratio'] = df['close'] / df['open']

        # Add sentiment features if requested
        if include_sentiment and symbol:
            try:
                sentiment_analyzer = SentimentAnalyzer()
                sentiment_features = sentiment_analyzer.get_sentiment_features(symbol)

                # Add sentiment features to all rows (same value for all)
                for key, value in sentiment_features.items():
                    features_df[key] = value

                logger.info("Sentiment features added")
            except Exception as e:
                logger.warning(f"Could not add sentiment features: {e}")

        # Remove infinite and NaN values
        features_df = features_df.replace([np.inf, -np.inf], np.nan)
        features_df = features_df.fillna(method='ffill').fillna(0)

        logger.info(f"Prepared {len(features_df.columns)} features")

        return features_df

    def create_labels(self, df: pd.DataFrame, future_periods: int = 5,
                     threshold: float = 0.02) -> pd.Series:
        """
        Create labels for classification.

        Args:
            df: DataFrame with OHLCV data
            future_periods: Periods to look ahead
            threshold: Minimum return threshold for positive class

        Returns:
            Series with labels (1 for buy, 0 for hold/sell)
        """
        # Calculate future returns
        future_returns = df['close'].shift(-future_periods) / df['close'] - 1

        # Create binary labels
        labels = (future_returns > threshold).astype(int)

        logger.info(f"Created labels with {labels.sum()} positive samples out of {len(labels)}")

        return labels

    def train(self, df: pd.DataFrame, symbol: Optional[str] = None,
             test_size: float = 0.2, future_periods: int = 5) -> Dict[str, float]:
        """
        Train ML models.

        Args:
            df: DataFrame with OHLCV data
            symbol: Symbol for sentiment analysis
            test_size: Test set size
            future_periods: Periods to look ahead for labels

        Returns:
            Dictionary with model scores
        """
        logger.info("Training ML models...")

        # Prepare features and labels
        features_df = self.prepare_features(df, include_sentiment=True, symbol=symbol)
        labels = self.create_labels(df, future_periods=future_periods)

        # Align features and labels (remove NaN from labels)
        valid_indices = ~labels.isna()
        features_df = features_df[valid_indices]
        labels = labels[valid_indices]

        # Store feature columns
        self.feature_columns = features_df.columns.tolist()

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            features_df, labels, test_size=test_size, random_state=42, shuffle=False
        )

        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # Train models
        scores = {}

        for name, model in self.models.items():
            try:
                logger.info(f"Training {name}...")

                # Train
                model.fit(X_train_scaled, y_train)

                # Evaluate
                y_pred = model.predict(X_test_scaled)

                accuracy = accuracy_score(y_test, y_pred)
                precision = precision_score(y_test, y_pred, zero_division=0)
                recall = recall_score(y_test, y_pred, zero_division=0)
                f1 = f1_score(y_test, y_pred, zero_division=0)

                scores[name] = {
                    'accuracy': accuracy,
                    'precision': precision,
                    'recall': recall,
                    'f1': f1,
                }

                logger.info(f"{name} - Accuracy: {accuracy:.3f}, Precision: {precision:.3f}, "
                          f"Recall: {recall:.3f}, F1: {f1:.3f}")

                # Save model
                self.save_model(name, model)

            except Exception as e:
                logger.error(f"Error training {name}: {e}")

        self.trained = True
        logger.info("Training complete")

        return scores

    def predict(self, df: pd.DataFrame, symbol: Optional[str] = None,
               ensemble: bool = True) -> Tuple[int, float]:
        """
        Make prediction using trained models.

        Args:
            df: DataFrame with OHLCV data
            symbol: Symbol for sentiment analysis
            ensemble: Use ensemble of all models

        Returns:
            Tuple of (prediction, confidence)
            prediction: 1 for buy, 0 for hold/sell
            confidence: Probability/confidence of prediction
        """
        if not self.trained:
            logger.warning("Models not trained yet")
            return 0, 0.0

        # Prepare features
        features_df = self.prepare_features(df, include_sentiment=True, symbol=symbol)

        # Use only the last row for prediction
        features = features_df.iloc[-1:][self.feature_columns]

        # Scale features
        features_scaled = self.scaler.transform(features)

        if ensemble:
            # Ensemble prediction (majority vote with confidence)
            predictions = []
            probabilities = []

            for name, model in self.models.items():
                try:
                    pred = model.predict(features_scaled)[0]
                    predictions.append(pred)

                    # Get probability if available
                    if hasattr(model, 'predict_proba'):
                        prob = model.predict_proba(features_scaled)[0]
                        probabilities.append(prob[1])  # Probability of class 1
                    else:
                        probabilities.append(pred)

                except Exception as e:
                    logger.warning(f"Error in {name} prediction: {e}")

            # Majority vote
            final_prediction = int(np.round(np.mean(predictions)))

            # Average confidence
            final_confidence = np.mean(probabilities)

        else:
            # Use single model (XGBoost by default)
            model = self.models['xgboost']
            final_prediction = model.predict(features_scaled)[0]

            if hasattr(model, 'predict_proba'):
                proba = model.predict_proba(features_scaled)[0]
                final_confidence = proba[final_prediction]
            else:
                final_confidence = 1.0 if final_prediction == 1 else 0.0

        logger.info(f"ML Prediction: {final_prediction} (confidence: {final_confidence:.3f})")

        return final_prediction, final_confidence

    def get_feature_importance(self, model_name: str = 'xgboost',
                              top_n: int = 20) -> pd.DataFrame:
        """
        Get feature importance from a model.

        Args:
            model_name: Model to get importance from
            top_n: Number of top features to return

        Returns:
            DataFrame with feature importance
        """
        if not self.trained:
            logger.warning("Models not trained yet")
            return pd.DataFrame()

        model = self.models.get(model_name)
        if model is None:
            logger.error(f"Model {model_name} not found")
            return pd.DataFrame()

        if hasattr(model, 'feature_importances_'):
            importance = model.feature_importances_
            importance_df = pd.DataFrame({
                'feature': self.feature_columns,
                'importance': importance
            })
            importance_df = importance_df.sort_values('importance', ascending=False)
            return importance_df.head(top_n)
        else:
            logger.warning(f"Model {model_name} does not have feature_importances_")
            return pd.DataFrame()

    def save_model(self, model_name: str, model: Any):
        """Save a trained model."""
        try:
            model_path = os.path.join(self.model_dir, f'{model_name}.pkl')
            with open(model_path, 'wb') as f:
                pickle.dump(model, f)

            # Save scaler
            scaler_path = os.path.join(self.model_dir, 'scaler.pkl')
            with open(scaler_path, 'wb') as f:
                pickle.dump(self.scaler, f)

            # Save feature columns
            features_path = os.path.join(self.model_dir, 'features.pkl')
            with open(features_path, 'wb') as f:
                pickle.dump(self.feature_columns, f)

            logger.info(f"Model {model_name} saved")
        except Exception as e:
            logger.error(f"Error saving model: {e}")

    def load_model(self, model_name: str):
        """Load a trained model."""
        try:
            model_path = os.path.join(self.model_dir, f'{model_name}.pkl')
            with open(model_path, 'rb') as f:
                self.models[model_name] = pickle.load(f)

            # Load scaler
            scaler_path = os.path.join(self.model_dir, 'scaler.pkl')
            with open(scaler_path, 'rb') as f:
                self.scaler = pickle.load(f)

            # Load feature columns
            features_path = os.path.join(self.model_dir, 'features.pkl')
            with open(features_path, 'rb') as f:
                self.feature_columns = pickle.load(f)

            self.trained = True
            logger.info(f"Model {model_name} loaded")
        except Exception as e:
            logger.error(f"Error loading model: {e}")

    def load_all_models(self):
        """Load all trained models."""
        for model_name in self.models.keys():
            self.load_model(model_name)
