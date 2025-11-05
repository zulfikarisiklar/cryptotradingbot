"""
Signal scanner for discovering trading opportunities across multiple symbols.
Scans markets and ranks symbols by signal strength.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.exchange.futures_client import BinanceFuturesClient
from src.indicators.technical_indicators import TechnicalIndicators
from src.ml.ml_engine import MLEngine
from src.sentiment.sentiment_analyzer import SentimentAnalyzer

logger = logging.getLogger(__name__)


class TradingSignal:
    """Represents a trading signal for a symbol."""

    def __init__(self, symbol: str, direction: str, strength: float,
                 entry_price: float, stop_loss: float, take_profit: float,
                 reasons: List[str]):
        """
        Initialize trading signal.

        Args:
            symbol: Trading pair
            direction: 'long' or 'short'
            strength: Signal strength (0-100)
            entry_price: Suggested entry price
            stop_loss: Suggested stop loss
            take_profit: Suggested take profit
            reasons: List of reasons for the signal
        """
        self.symbol = symbol
        self.direction = direction
        self.strength = strength
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.reasons = reasons
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict:
        """Convert signal to dictionary."""
        return {
            'symbol': self.symbol,
            'direction': self.direction,
            'strength': self.strength,
            'entry_price': self.entry_price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'reasons': self.reasons,
            'timestamp': self.timestamp,
        }

    def __repr__(self):
        return f"Signal({self.symbol} {self.direction} {self.strength:.1f})"


class SignalScanner:
    """
    Scans multiple symbols for trading opportunities.
    """

    def __init__(self, client: BinanceFuturesClient, ml_engine: Optional[MLEngine] = None,
                 sentiment_analyzer: Optional[SentimentAnalyzer] = None,
                 timeframe: str = '1h'):
        """
        Initialize signal scanner.

        Args:
            client: Futures client
            ml_engine: ML engine for predictions
            sentiment_analyzer: Sentiment analyzer
            timeframe: Timeframe for analysis
        """
        self.client = client
        self.ml_engine = ml_engine
        self.sentiment_analyzer = sentiment_analyzer
        self.timeframe = timeframe

        # Scanner configuration
        self.min_signal_strength = 60  # Minimum 60% strength to consider
        self.max_symbols_to_scan = 50  # Scan top 50 by volume
        self.atr_multiplier_sl = 2.0  # Stop loss ATR multiplier
        self.atr_multiplier_tp = 3.0  # Take profit ATR multiplier

        logger.info(f"SignalScanner initialized for {timeframe} timeframe")

    def get_top_symbols(self, limit: int = 50) -> List[str]:
        """
        Get top symbols by 24h volume.

        Args:
            limit: Number of symbols to return

        Returns:
            List of symbol names
        """
        try:
            # Get all available symbols
            all_symbols = self.client.get_available_symbols()

            # Filter for USDT perpetuals only
            usdt_symbols = [s for s in all_symbols if 'USDT' in s and ':' not in s]

            # Get tickers to sort by volume
            volume_data = []
            for symbol in usdt_symbols[:200]:  # Limit initial fetch
                try:
                    ticker = self.client.fetch_ticker(symbol)
                    volume_data.append({
                        'symbol': symbol,
                        'volume': ticker.get('quoteVolume', 0)
                    })
                except:
                    continue

            # Sort by volume and return top N
            volume_df = pd.DataFrame(volume_data)
            if not volume_df.empty:
                volume_df = volume_df.sort_values('volume', ascending=False)
                top_symbols = volume_df.head(limit)['symbol'].tolist()
                logger.info(f"Selected top {len(top_symbols)} symbols by volume")
                return top_symbols

            return usdt_symbols[:limit]

        except Exception as e:
            logger.error(f"Error getting top symbols: {e}")
            # Return some default popular symbols
            return ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT']

    def analyze_symbol(self, symbol: str) -> Optional[TradingSignal]:
        """
        Analyze a single symbol for trading signals.

        Args:
            symbol: Trading pair

        Returns:
            TradingSignal or None
        """
        try:
            # Fetch data
            df = self.client.fetch_ohlcv(symbol, self.timeframe, limit=500)

            if df.empty or len(df) < 200:
                return None

            current_price = df['close'].iloc[-1]

            # Calculate technical indicators
            tech_indicators = TechnicalIndicators(df)
            df_with_indicators = tech_indicators.calculate_all_indicators()

            # Get latest values
            latest = df_with_indicators.iloc[-1]

            # Analyze for signals
            signal_strength = 0
            direction = None
            reasons = []

            # === BULLISH SIGNALS ===
            bullish_score = 0

            # RSI oversold
            if 'RSI_14' in latest and latest['RSI_14'] < 40:
                bullish_score += 15
                reasons.append(f"RSI oversold ({latest['RSI_14']:.1f})")

            # MACD crossover
            if 'MACD' in latest and 'MACD_SIGNAL' in latest:
                if latest['MACD'] > latest['MACD_SIGNAL'] and latest['MACD_HIST'] > 0:
                    bullish_score += 15
                    reasons.append("MACD bullish crossover")

            # Price above key MAs
            if 'SMA_50' in latest and 'SMA_200' in latest:
                if latest['close'] > latest['SMA_50'] > latest['SMA_200']:
                    bullish_score += 10
                    reasons.append("Price above 50/200 SMA (uptrend)")

            # Stochastic oversold
            if 'STOCH_K' in latest and latest['STOCH_K'] < 30:
                bullish_score += 10
                reasons.append(f"Stochastic oversold ({latest['STOCH_K']:.1f})")

            # Volume increase
            if 'volume_ratio_20' in latest and latest['volume_ratio_20'] > 1.5:
                bullish_score += 10
                reasons.append(f"Volume spike ({latest['volume_ratio_20']:.1f}x)")

            # Bollinger Bands
            if 'BB_LOWER_20' in latest and latest['close'] < latest['BB_LOWER_20']:
                bullish_score += 10
                reasons.append("Price below lower Bollinger Band")

            # ADX strong trend
            if 'ADX' in latest and latest['ADX'] > 25:
                if 'PLUS_DI' in latest and 'MINUS_DI' in latest:
                    if latest['PLUS_DI'] > latest['MINUS_DI']:
                        bullish_score += 10
                        reasons.append(f"Strong uptrend (ADX {latest['ADX']:.1f})")

            # Bullish candlestick patterns
            bullish_patterns = ['CDLHAMMER', 'CDLMORNINGSTAR', 'CDLENGULFING', 'CDLPIERCING']
            for pattern in bullish_patterns:
                if pattern in latest and latest[pattern] > 0:
                    bullish_score += 5
                    reasons.append(f"Bullish pattern: {pattern}")
                    break

            # ML prediction (if available)
            if self.ml_engine and self.ml_engine.trained:
                try:
                    prediction, confidence = self.ml_engine.predict(df, symbol=symbol, ensemble=True)
                    if prediction == 1 and confidence > 0.6:
                        bullish_score += confidence * 20
                        reasons.append(f"ML bullish prediction ({confidence:.2f})")
                except:
                    pass

            # === BEARISH SIGNALS ===
            bearish_score = 0

            # RSI overbought
            if 'RSI_14' in latest and latest['RSI_14'] > 70:
                bearish_score += 15
                reasons.append(f"RSI overbought ({latest['RSI_14']:.1f})")

            # MACD bearish crossover
            if 'MACD' in latest and 'MACD_SIGNAL' in latest:
                if latest['MACD'] < latest['MACD_SIGNAL'] and latest['MACD_HIST'] < 0:
                    bearish_score += 15
                    reasons.append("MACD bearish crossover")

            # Price below key MAs
            if 'SMA_50' in latest and 'SMA_200' in latest:
                if latest['close'] < latest['SMA_50'] < latest['SMA_200']:
                    bearish_score += 10
                    reasons.append("Price below 50/200 SMA (downtrend)")

            # Stochastic overbought
            if 'STOCH_K' in latest and latest['STOCH_K'] > 70:
                bearish_score += 10
                reasons.append(f"Stochastic overbought ({latest['STOCH_K']:.1f})")

            # Bollinger Bands
            if 'BB_UPPER_20' in latest and latest['close'] > latest['BB_UPPER_20']:
                bearish_score += 10
                reasons.append("Price above upper Bollinger Band")

            # ADX strong downtrend
            if 'ADX' in latest and latest['ADX'] > 25:
                if 'PLUS_DI' in latest and 'MINUS_DI' in latest:
                    if latest['MINUS_DI'] > latest['PLUS_DI']:
                        bearish_score += 10
                        reasons.append(f"Strong downtrend (ADX {latest['ADX']:.1f})")

            # Bearish candlestick patterns
            bearish_patterns = ['CDLHANGINGMAN', 'CDLEVENINGSTAR', 'CDLSHOOTINGSTAR']
            for pattern in bearish_patterns:
                if pattern in latest and latest[pattern] < 0:
                    bearish_score += 5
                    reasons.append(f"Bearish pattern: {pattern}")
                    break

            # Determine direction and strength
            if bullish_score > bearish_score and bullish_score >= self.min_signal_strength:
                direction = 'long'
                signal_strength = bullish_score
            elif bearish_score > bullish_score and bearish_score >= self.min_signal_strength:
                direction = 'short'
                signal_strength = bearish_score
            else:
                return None  # No strong signal

            # Calculate stop loss and take profit using ATR
            atr = tech_indicators.get_atr(period=14)[-1]

            if direction == 'long':
                stop_loss = current_price - (atr * self.atr_multiplier_sl)
                take_profit = current_price + (atr * self.atr_multiplier_tp)
            else:  # short
                stop_loss = current_price + (atr * self.atr_multiplier_sl)
                take_profit = current_price - (atr * self.atr_multiplier_tp)

            # Create signal
            signal = TradingSignal(
                symbol=symbol,
                direction=direction,
                strength=min(signal_strength, 100),  # Cap at 100
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                reasons=reasons
            )

            return signal

        except Exception as e:
            logger.debug(f"Error analyzing {symbol}: {e}")
            return None

    def scan_market(self, max_workers: int = 5, exclude_symbols: Optional[List[str]] = None) -> List[TradingSignal]:
        """
        Scan market for trading signals across multiple symbols.

        Args:
            max_workers: Number of concurrent workers
            exclude_symbols: Symbols to exclude from scan

        Returns:
            List of trading signals sorted by strength
        """
        logger.info(f"Starting market scan...")

        # Get symbols to scan
        symbols_to_scan = self.get_top_symbols(self.max_symbols_to_scan)

        # Exclude symbols we already have positions in
        if exclude_symbols:
            symbols_to_scan = [s for s in symbols_to_scan if s not in exclude_symbols]

        logger.info(f"Scanning {len(symbols_to_scan)} symbols for opportunities...")

        # Scan symbols concurrently
        signals = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_symbol = {
                executor.submit(self.analyze_symbol, symbol): symbol
                for symbol in symbols_to_scan
            }

            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    signal = future.result()
                    if signal:
                        signals.append(signal)
                        logger.info(f"Signal found: {signal}")
                except Exception as e:
                    logger.debug(f"Error processing {symbol}: {e}")

        # Sort by signal strength
        signals.sort(key=lambda x: x.strength, reverse=True)

        logger.info(f"Market scan complete: Found {len(signals)} signals")

        return signals

    def get_best_signal(self, exclude_symbols: Optional[List[str]] = None) -> Optional[TradingSignal]:
        """
        Get the best trading signal from market scan.

        Args:
            exclude_symbols: Symbols to exclude

        Returns:
            Best trading signal or None
        """
        signals = self.scan_market(exclude_symbols=exclude_symbols)

        if signals:
            return signals[0]  # Return strongest signal

        return None
