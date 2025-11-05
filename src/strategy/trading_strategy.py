"""
Trading strategy with take profit, stop loss, and pyramid mode.
Uses ATR for dynamic take profit calculations.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging
import talib

from src.config import config

logger = logging.getLogger(__name__)


class Position:
    """Represents a trading position."""

    def __init__(self, symbol: str, side: str, entry_price: float,
                 amount: float, timestamp: datetime):
        """
        Initialize a position.

        Args:
            symbol: Trading pair
            side: 'long' or 'short'
            entry_price: Entry price
            amount: Position size
            timestamp: Entry timestamp
        """
        self.symbol = symbol
        self.side = side
        self.entry_price = entry_price
        self.amount = amount
        self.timestamp = timestamp
        self.current_price = entry_price
        self.pyramid_levels = [{'price': entry_price, 'amount': amount}]

    def update_price(self, price: float):
        """Update current price."""
        self.current_price = price

    def get_unrealized_pnl(self) -> float:
        """Get unrealized profit/loss."""
        if self.side == 'long':
            return (self.current_price - self.entry_price) * self.amount
        else:  # short
            return (self.entry_price - self.current_price) * self.amount

    def get_unrealized_pnl_percent(self) -> float:
        """Get unrealized profit/loss percentage."""
        if self.side == 'long':
            return (self.current_price / self.entry_price - 1) * 100
        else:  # short
            return (self.entry_price / self.current_price - 1) * 100

    def add_pyramid_level(self, price: float, amount: float):
        """Add a pyramid level to the position."""
        self.pyramid_levels.append({'price': price, 'amount': amount})

        # Recalculate average entry price
        total_cost = sum(level['price'] * level['amount'] for level in self.pyramid_levels)
        total_amount = sum(level['amount'] for level in self.pyramid_levels)

        self.entry_price = total_cost / total_amount
        self.amount = total_amount

    def get_pyramid_count(self) -> int:
        """Get number of pyramid levels."""
        return len(self.pyramid_levels)


class ATRCalculator:
    """ATR-based calculations for stop loss and take profit."""

    @staticmethod
    def calculate_atr(high: np.ndarray, low: np.ndarray,
                     close: np.ndarray, period: int = 14) -> np.ndarray:
        """
        Calculate ATR (Average True Range).

        Args:
            high: High prices
            low: Low prices
            close: Close prices
            period: ATR period

        Returns:
            ATR values
        """
        return talib.ATR(high, low, close, timeperiod=period)

    @staticmethod
    def get_atr_stop_loss(entry_price: float, atr: float,
                         side: str, multiplier: float = 2.0) -> float:
        """
        Calculate ATR-based stop loss.

        Args:
            entry_price: Entry price
            atr: Current ATR value
            side: 'long' or 'short'
            multiplier: ATR multiplier

        Returns:
            Stop loss price
        """
        if side == 'long':
            return entry_price - (atr * multiplier)
        else:  # short
            return entry_price + (atr * multiplier)

    @staticmethod
    def get_atr_take_profit(entry_price: float, atr: float,
                           side: str, multiplier: float = 3.0) -> float:
        """
        Calculate ATR-based take profit.

        Args:
            entry_price: Entry price
            atr: Current ATR value
            side: 'long' or 'short'
            multiplier: ATR multiplier (default 3.0 for 1.5:1 reward/risk)

        Returns:
            Take profit price
        """
        if side == 'long':
            return entry_price + (atr * multiplier)
        else:  # short
            return entry_price - (atr * multiplier)

    @staticmethod
    def get_trailing_stop(current_price: float, atr: float,
                         side: str, multiplier: float = 2.0) -> float:
        """
        Calculate trailing stop loss.

        Args:
            current_price: Current price
            atr: Current ATR value
            side: 'long' or 'short'
            multiplier: ATR multiplier

        Returns:
            Trailing stop price
        """
        if side == 'long':
            return current_price - (atr * multiplier)
        else:  # short
            return current_price + (atr * multiplier)


class TradingStrategy:
    """
    Main trading strategy with take profit, stop loss, and pyramid mode.
    """

    def __init__(self, symbol: str, initial_capital: float = 10000):
        """
        Initialize trading strategy.

        Args:
            symbol: Trading pair
            initial_capital: Initial capital
        """
        self.symbol = symbol
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.position: Optional[Position] = None

        # Strategy parameters
        self.stop_loss_percent = config.STOP_LOSS_PERCENT
        self.take_profit_multiplier = config.TAKE_PROFIT_MULTIPLIER
        self.max_pyramid_levels = config.MAX_PYRAMID_LEVELS
        self.position_size = config.MAX_POSITION_SIZE

        # ATR parameters
        self.atr_period = 14
        self.atr_sl_multiplier = 2.0
        self.atr_tp_multiplier = self.take_profit_multiplier

        # Trailing stop
        self.use_trailing_stop = True
        self.trailing_stop_price = None

        # Trade history
        self.trade_history = []

        logger.info(f"TradingStrategy initialized for {symbol}")

    def calculate_position_size(self, price: float, risk_percent: float = None) -> float:
        """
        Calculate position size based on available capital.

        Args:
            price: Current price
            risk_percent: Risk percentage (uses config if not provided)

        Returns:
            Position size in base currency
        """
        if risk_percent is None:
            risk_percent = self.position_size

        # Maximum capital to risk
        risk_capital = self.capital * risk_percent

        # Calculate position size
        position_size = risk_capital / price

        return position_size

    def check_entry_signal(self, df: pd.DataFrame, ml_prediction: int,
                          ml_confidence: float, sentiment_signal: float) -> bool:
        """
        Check if entry conditions are met.

        Args:
            df: DataFrame with OHLCV and indicators
            ml_prediction: ML model prediction (1=buy, 0=hold/sell)
            ml_confidence: ML prediction confidence
            sentiment_signal: Sentiment signal (-1 to 1)

        Returns:
            True if entry signal, False otherwise
        """
        # Require ML buy signal with sufficient confidence
        if ml_prediction != 1 or ml_confidence < 0.6:
            return False

        # Check sentiment (optional, can be disabled)
        if config.ENABLE_SENTIMENT and sentiment_signal < -0.3:
            logger.info("Entry blocked by negative sentiment")
            return False

        # Additional technical filters
        latest = df.iloc[-1]

        # Trend filter: Price above 50 SMA
        if 'SMA_50' in df.columns:
            if latest['close'] < latest['SMA_50']:
                logger.info("Entry blocked: Price below 50 SMA")
                return False

        # Momentum filter: RSI not overbought
        if 'RSI_14' in df.columns:
            if latest['RSI_14'] > 70:
                logger.info("Entry blocked: RSI overbought")
                return False

        # Volume filter: Above average volume
        if 'volume_sma_20' in df.columns:
            if latest['volume'] < latest['volume_sma_20'] * 0.8:
                logger.info("Entry blocked: Low volume")
                return False

        logger.info("Entry signal confirmed")
        return True

    def open_position(self, df: pd.DataFrame, timestamp: datetime) -> Dict:
        """
        Open a new position.

        Args:
            df: DataFrame with OHLCV data
            timestamp: Current timestamp

        Returns:
            Trade information
        """
        if self.position is not None:
            logger.warning("Position already open")
            return {}

        current_price = df.iloc[-1]['close']

        # Calculate ATR
        atr = ATRCalculator.calculate_atr(
            df['high'].values,
            df['low'].values,
            df['close'].values,
            period=self.atr_period
        )[-1]

        # Calculate position size
        amount = self.calculate_position_size(current_price)

        # Create position
        self.position = Position(
            symbol=self.symbol,
            side='long',
            entry_price=current_price,
            amount=amount,
            timestamp=timestamp
        )

        # Calculate stop loss and take profit
        stop_loss = ATRCalculator.get_atr_stop_loss(
            current_price, atr, 'long', self.atr_sl_multiplier
        )

        take_profit = ATRCalculator.get_atr_take_profit(
            current_price, atr, 'long', self.atr_tp_multiplier
        )

        # Initialize trailing stop
        if self.use_trailing_stop:
            self.trailing_stop_price = stop_loss

        # Update capital
        position_value = current_price * amount
        self.capital -= position_value

        trade_info = {
            'action': 'OPEN',
            'timestamp': timestamp,
            'price': current_price,
            'amount': amount,
            'side': 'long',
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'atr': atr,
            'position_value': position_value,
        }

        self.trade_history.append(trade_info)

        logger.info(f"Position opened: {amount:.6f} @ {current_price:.2f}, "
                   f"SL: {stop_loss:.2f}, TP: {take_profit:.2f}")

        return trade_info

    def check_pyramid_entry(self, df: pd.DataFrame, ml_confidence: float) -> bool:
        """
        Check if conditions are met for pyramid entry.

        Args:
            df: DataFrame with OHLCV data
            ml_confidence: ML prediction confidence

        Returns:
            True if pyramid entry allowed
        """
        if self.position is None:
            return False

        # Check if max pyramid levels reached
        if self.position.get_pyramid_count() >= self.max_pyramid_levels:
            return False

        # Check if position is profitable
        if self.position.get_unrealized_pnl_percent() < 1.0:
            return False

        # Check ML confidence
        if ml_confidence < 0.7:
            return False

        # Check trend continuation
        latest = df.iloc[-1]
        if 'RSI_14' in df.columns and latest['RSI_14'] > 75:
            return False

        logger.info("Pyramid entry conditions met")
        return True

    def add_pyramid_level(self, df: pd.DataFrame, timestamp: datetime) -> Dict:
        """
        Add a pyramid level to existing position.

        Args:
            df: DataFrame with OHLCV data
            timestamp: Current timestamp

        Returns:
            Trade information
        """
        if self.position is None:
            return {}

        current_price = df.iloc[-1]['close']

        # Calculate reduced position size for pyramid
        base_amount = self.calculate_position_size(current_price)
        pyramid_amount = base_amount * 0.5  # 50% of base size

        # Add pyramid level
        self.position.add_pyramid_level(current_price, pyramid_amount)

        # Update capital
        position_value = current_price * pyramid_amount
        self.capital -= position_value

        # Recalculate stop loss based on new average entry
        atr = ATRCalculator.calculate_atr(
            df['high'].values,
            df['low'].values,
            df['close'].values,
            period=self.atr_period
        )[-1]

        new_stop_loss = ATRCalculator.get_atr_stop_loss(
            self.position.entry_price, atr, 'long', self.atr_sl_multiplier
        )

        # Update trailing stop
        if self.use_trailing_stop:
            self.trailing_stop_price = max(self.trailing_stop_price, new_stop_loss)

        trade_info = {
            'action': 'PYRAMID',
            'timestamp': timestamp,
            'price': current_price,
            'amount': pyramid_amount,
            'total_amount': self.position.amount,
            'avg_entry': self.position.entry_price,
            'pyramid_level': self.position.get_pyramid_count(),
        }

        self.trade_history.append(trade_info)

        logger.info(f"Pyramid level {self.position.get_pyramid_count()} added: "
                   f"{pyramid_amount:.6f} @ {current_price:.2f}, "
                   f"New avg: {self.position.entry_price:.2f}")

        return trade_info

    def check_exit_signal(self, df: pd.DataFrame) -> Tuple[bool, str]:
        """
        Check if exit conditions are met.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Tuple of (should_exit, reason)
        """
        if self.position is None:
            return False, ""

        current_price = df.iloc[-1]['close']
        self.position.update_price(current_price)

        # Calculate ATR for dynamic stops
        atr = ATRCalculator.calculate_atr(
            df['high'].values,
            df['low'].values,
            df['close'].values,
            period=self.atr_period
        )[-1]

        # Calculate take profit
        take_profit = ATRCalculator.get_atr_take_profit(
            self.position.entry_price, atr, 'long', self.atr_tp_multiplier
        )

        # Update trailing stop
        if self.use_trailing_stop:
            new_trailing_stop = ATRCalculator.get_trailing_stop(
                current_price, atr, 'long', self.atr_sl_multiplier
            )
            self.trailing_stop_price = max(self.trailing_stop_price, new_trailing_stop)

        # Check take profit
        if current_price >= take_profit:
            return True, "TAKE_PROFIT"

        # Check trailing stop
        if self.use_trailing_stop and current_price <= self.trailing_stop_price:
            return True, "TRAILING_STOP"

        # Check fixed stop loss (fallback)
        stop_loss = ATRCalculator.get_atr_stop_loss(
            self.position.entry_price, atr, 'long', self.atr_sl_multiplier
        )
        if current_price <= stop_loss:
            return True, "STOP_LOSS"

        # Check for trend reversal
        latest = df.iloc[-1]
        if 'RSI_14' in df.columns and latest['RSI_14'] < 30:
            return True, "REVERSAL_SIGNAL"

        return False, ""

    def close_position(self, df: pd.DataFrame, timestamp: datetime, reason: str) -> Dict:
        """
        Close current position.

        Args:
            df: DataFrame with OHLCV data
            timestamp: Current timestamp
            reason: Reason for closing

        Returns:
            Trade information
        """
        if self.position is None:
            logger.warning("No position to close")
            return {}

        current_price = df.iloc[-1]['close']
        self.position.update_price(current_price)

        # Calculate P&L
        pnl = self.position.get_unrealized_pnl()
        pnl_percent = self.position.get_unrealized_pnl_percent()

        # Update capital
        position_value = current_price * self.position.amount
        self.capital += position_value

        trade_info = {
            'action': 'CLOSE',
            'timestamp': timestamp,
            'price': current_price,
            'amount': self.position.amount,
            'entry_price': self.position.entry_price,
            'pnl': pnl,
            'pnl_percent': pnl_percent,
            'reason': reason,
            'capital': self.capital,
            'pyramid_levels': self.position.get_pyramid_count(),
        }

        self.trade_history.append(trade_info)

        logger.info(f"Position closed: {self.position.amount:.6f} @ {current_price:.2f}, "
                   f"P&L: {pnl:.2f} ({pnl_percent:.2f}%), Reason: {reason}")

        # Clear position
        self.position = None
        self.trailing_stop_price = None

        return trade_info

    def get_performance_stats(self) -> Dict:
        """Get performance statistics."""
        if not self.trade_history:
            return {}

        closed_trades = [t for t in self.trade_history if t['action'] == 'CLOSE']

        if not closed_trades:
            return {'total_trades': 0}

        pnls = [t['pnl'] for t in closed_trades]
        winning_trades = [p for p in pnls if p > 0]
        losing_trades = [p for p in pnls if p < 0]

        stats = {
            'total_trades': len(closed_trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': len(winning_trades) / len(closed_trades) * 100,
            'total_pnl': sum(pnls),
            'avg_win': np.mean(winning_trades) if winning_trades else 0,
            'avg_loss': np.mean(losing_trades) if losing_trades else 0,
            'largest_win': max(pnls) if pnls else 0,
            'largest_loss': min(pnls) if pnls else 0,
            'final_capital': self.capital,
            'total_return': (self.capital / self.initial_capital - 1) * 100,
        }

        return stats
