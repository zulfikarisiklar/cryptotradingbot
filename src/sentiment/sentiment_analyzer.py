"""
Sentiment analysis module for news and social media.
Uses NLP techniques to analyze market sentiment.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import logging
import requests
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import nltk
from bs4 import BeautifulSoup

from src.config import config

logger = logging.getLogger(__name__)

# Download required NLTK data
try:
    nltk.download('vader_lexicon', quiet=True)
    nltk.download('punkt', quiet=True)
except:
    pass


class SentimentAnalyzer:
    """
    Sentiment analysis for cryptocurrency market sentiment.
    Analyzes news articles, headlines, and text data.
    """

    def __init__(self, news_api_key: Optional[str] = None):
        """
        Initialize sentiment analyzer.

        Args:
            news_api_key: NewsAPI key for fetching news
        """
        self.news_api_key = news_api_key or config.NEWS_API_KEY
        self.vader = SentimentIntensityAnalyzer()

        # Custom crypto-specific sentiment words
        self._add_crypto_lexicon()

        logger.info("SentimentAnalyzer initialized")

    def _add_crypto_lexicon(self):
        """Add cryptocurrency-specific words to VADER lexicon."""
        crypto_words = {
            'moon': 3.0,
            'lambo': 3.0,
            'hodl': 2.5,
            'bullish': 3.0,
            'bearish': -3.0,
            'pump': 2.0,
            'dump': -2.5,
            'fud': -2.5,
            'fomo': 1.5,
            'whale': 1.0,
            'dip': -1.5,
            'ath': 3.0,  # All-time high
            'crash': -3.0,
            'rally': 2.5,
            'breakthrough': 2.0,
            'resistance': -0.5,
            'support': 0.5,
        }

        for word, score in crypto_words.items():
            self.vader.lexicon[word] = score

    def analyze_text(self, text: str) -> Dict[str, float]:
        """
        Analyze sentiment of a single text.

        Args:
            text: Text to analyze

        Returns:
            Dictionary with sentiment scores
        """
        if not text:
            return {'compound': 0.0, 'pos': 0.0, 'neu': 1.0, 'neg': 0.0}

        # VADER sentiment
        vader_scores = self.vader.polarity_scores(text)

        # TextBlob sentiment
        blob = TextBlob(text)
        textblob_polarity = blob.sentiment.polarity
        textblob_subjectivity = blob.sentiment.subjectivity

        return {
            'compound': vader_scores['compound'],
            'positive': vader_scores['pos'],
            'neutral': vader_scores['neu'],
            'negative': vader_scores['neg'],
            'textblob_polarity': textblob_polarity,
            'textblob_subjectivity': textblob_subjectivity,
        }

    def fetch_crypto_news(self, symbol: str, days: int = 7) -> List[Dict]:
        """
        Fetch cryptocurrency news from NewsAPI.

        Args:
            symbol: Cryptocurrency symbol (e.g., 'BTC', 'ETH')
            days: Number of days to look back

        Returns:
            List of news articles
        """
        if not self.news_api_key:
            logger.warning("NewsAPI key not configured")
            return []

        # Extract base symbol (e.g., 'BTC' from 'BTC/USDT')
        base_symbol = symbol.split('/')[0] if '/' in symbol else symbol

        # Prepare search query
        queries = [
            base_symbol,
            f"{base_symbol} cryptocurrency",
            f"{base_symbol} crypto",
        ]

        all_articles = []

        for query in queries:
            try:
                url = 'https://newsapi.org/v2/everything'
                params = {
                    'q': query,
                    'apiKey': self.news_api_key,
                    'language': 'en',
                    'sortBy': 'publishedAt',
                    'from': (datetime.now() - timedelta(days=days)).isoformat(),
                    'to': datetime.now().isoformat(),
                }

                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()

                data = response.json()
                articles = data.get('articles', [])
                all_articles.extend(articles)

            except Exception as e:
                logger.error(f"Error fetching news for {query}: {e}")

        # Remove duplicates based on title
        seen_titles = set()
        unique_articles = []
        for article in all_articles:
            title = article.get('title', '')
            if title and title not in seen_titles:
                seen_titles.add(title)
                unique_articles.append(article)

        logger.info(f"Fetched {len(unique_articles)} unique news articles for {symbol}")
        return unique_articles

    def analyze_news_sentiment(self, symbol: str, days: int = 7) -> Dict[str, float]:
        """
        Analyze sentiment from news articles.

        Args:
            symbol: Cryptocurrency symbol
            days: Number of days to look back

        Returns:
            Aggregated sentiment scores
        """
        articles = self.fetch_crypto_news(symbol, days)

        if not articles:
            return {
                'avg_compound': 0.0,
                'avg_positive': 0.0,
                'avg_neutral': 1.0,
                'avg_negative': 0.0,
                'article_count': 0,
                'bullish_ratio': 0.5,
            }

        sentiments = []

        for article in articles:
            # Combine title and description for analysis
            text = f"{article.get('title', '')} {article.get('description', '')}"
            sentiment = self.analyze_text(text)
            sentiments.append(sentiment)

        # Aggregate sentiments
        df = pd.DataFrame(sentiments)

        # Calculate bullish ratio (positive compound scores)
        bullish_count = (df['compound'] > 0.05).sum()
        bearish_count = (df['compound'] < -0.05).sum()
        total_directional = bullish_count + bearish_count

        bullish_ratio = bullish_count / total_directional if total_directional > 0 else 0.5

        result = {
            'avg_compound': df['compound'].mean(),
            'avg_positive': df['positive'].mean(),
            'avg_neutral': df['neutral'].mean(),
            'avg_negative': df['negative'].mean(),
            'article_count': len(articles),
            'bullish_ratio': bullish_ratio,
            'sentiment_std': df['compound'].std(),
        }

        logger.info(f"News sentiment for {symbol}: compound={result['avg_compound']:.3f}, "
                   f"bullish_ratio={result['bullish_ratio']:.3f}")

        return result

    def get_sentiment_signal(self, symbol: str, days: int = 7) -> Tuple[float, str]:
        """
        Get trading signal based on sentiment analysis.

        Args:
            symbol: Cryptocurrency symbol
            days: Number of days to look back

        Returns:
            Tuple of (signal_strength, signal_direction)
            signal_strength: -1.0 to 1.0
            signal_direction: 'bullish', 'bearish', or 'neutral'
        """
        sentiment = self.analyze_news_sentiment(symbol, days)

        compound = sentiment['avg_compound']
        bullish_ratio = sentiment['bullish_ratio']

        # Combine compound score and bullish ratio
        signal_strength = (compound + (bullish_ratio - 0.5) * 2) / 2

        # Determine direction
        if signal_strength > 0.2:
            direction = 'bullish'
        elif signal_strength < -0.2:
            direction = 'bearish'
        else:
            direction = 'neutral'

        logger.info(f"Sentiment signal for {symbol}: {direction} ({signal_strength:.3f})")

        return signal_strength, direction

    def analyze_headlines_batch(self, headlines: List[str]) -> pd.DataFrame:
        """
        Analyze sentiment for multiple headlines.

        Args:
            headlines: List of headlines/texts

        Returns:
            DataFrame with sentiment analysis
        """
        results = []

        for headline in headlines:
            sentiment = self.analyze_text(headline)
            sentiment['text'] = headline
            results.append(sentiment)

        return pd.DataFrame(results)

    def get_fear_greed_proxy(self, symbol: str, days: int = 7) -> float:
        """
        Calculate a Fear & Greed proxy based on news sentiment.

        Args:
            symbol: Cryptocurrency symbol
            days: Number of days to look back

        Returns:
            Score from 0 (extreme fear) to 100 (extreme greed)
        """
        sentiment = self.analyze_news_sentiment(symbol, days)

        # Map compound score (-1 to 1) to 0-100 scale
        compound = sentiment['avg_compound']
        score = (compound + 1) * 50  # Maps -1->0, 0->50, 1->100

        # Adjust based on bullish ratio
        bullish_ratio = sentiment['bullish_ratio']
        score = score * 0.7 + bullish_ratio * 100 * 0.3

        # Clamp to 0-100
        score = max(0, min(100, score))

        logger.info(f"Fear & Greed proxy for {symbol}: {score:.1f}")

        return score

    def get_sentiment_features(self, symbol: str, days: int = 7) -> Dict[str, float]:
        """
        Get sentiment features for machine learning.

        Args:
            symbol: Cryptocurrency symbol
            days: Number of days to look back

        Returns:
            Dictionary of sentiment features
        """
        sentiment = self.analyze_news_sentiment(symbol, days)
        signal_strength, signal_direction = self.get_sentiment_signal(symbol, days)
        fear_greed = self.get_fear_greed_proxy(symbol, days)

        features = {
            'sentiment_compound': sentiment['avg_compound'],
            'sentiment_positive': sentiment['avg_positive'],
            'sentiment_negative': sentiment['avg_negative'],
            'sentiment_neutral': sentiment['avg_neutral'],
            'sentiment_bullish_ratio': sentiment['bullish_ratio'],
            'sentiment_std': sentiment.get('sentiment_std', 0),
            'sentiment_signal_strength': signal_strength,
            'sentiment_fear_greed': fear_greed / 100,  # Normalize to 0-1
            'sentiment_article_count': sentiment['article_count'],
        }

        return features


class VolumeAnalyzer:
    """Analyze volume patterns and anomalies."""

    @staticmethod
    def calculate_volume_features(df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate volume-based features.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with volume features
        """
        features = pd.DataFrame(index=df.index)

        # Volume moving averages
        features['volume_sma_5'] = df['volume'].rolling(5).mean()
        features['volume_sma_20'] = df['volume'].rolling(20).mean()
        features['volume_sma_50'] = df['volume'].rolling(50).mean()

        # Volume ratio
        features['volume_ratio_5'] = df['volume'] / features['volume_sma_5']
        features['volume_ratio_20'] = df['volume'] / features['volume_sma_20']

        # Volume trend
        features['volume_trend'] = df['volume'].pct_change(5)

        # Price-Volume correlation
        features['pv_corr_10'] = df['close'].rolling(10).corr(df['volume'])

        # Unusual volume (z-score)
        volume_mean = df['volume'].rolling(20).mean()
        volume_std = df['volume'].rolling(20).std()
        features['volume_zscore'] = (df['volume'] - volume_mean) / volume_std

        # Volume momentum
        features['volume_momentum'] = df['volume'].pct_change(1)

        return features

    @staticmethod
    def detect_volume_spikes(df: pd.DataFrame, threshold: float = 2.0) -> pd.Series:
        """
        Detect volume spikes.

        Args:
            df: DataFrame with volume data
            threshold: Standard deviation threshold

        Returns:
            Boolean series indicating volume spikes
        """
        volume_mean = df['volume'].rolling(20).mean()
        volume_std = df['volume'].rolling(20).std()
        zscore = (df['volume'] - volume_mean) / volume_std

        return zscore > threshold
