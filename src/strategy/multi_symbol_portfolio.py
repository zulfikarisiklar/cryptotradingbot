"""
Multi-symbol portfolio manager for futures trading.
Manages up to N positions across different symbols with leverage.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

from src.exchange.futures_client import BinanceFuturesClient
from src.strategy.trading_strategy import ATRCalculator

logger = logging.getLogger(__name__)


class FuturesPosition:
    """Represents a futures position with leverage."""

    def __init__(self, symbol: str, side: str, entry_price: float, amount: float,
                 leverage: int, stop_loss: float, take_profit: float,
                 timestamp: datetime):
        """
        Initialize futures position.

        Args:
            symbol: Trading pair
            side: 'long' or 'short'
            entry_price: Entry price
            amount: Position size (contracts)
            leverage: Leverage multiplier
            stop_loss: Stop loss price
            take_profit: Take profit price
            timestamp: Entry timestamp
        """
        self.symbol = symbol
        self.side = side
        self.entry_price = entry_price
        self.amount = amount
        self.leverage = leverage
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.timestamp = timestamp
        self.current_price = entry_price

        # Calculate position value and margin
        self.position_value = amount * entry_price
        self.margin_used = self.position_value / leverage

        # Track P&L
        self.unrealized_pnl = 0.0
        self.unrealized_pnl_percent = 0.0

        # Orders
        self.stop_loss_order_id = None
        self.take_profit_order_id = None

    def update_price(self, price: float):
        """Update current price and calculate P&L."""
        self.current_price = price

        # Calculate unrealized P&L
        if self.side == 'long':
            price_change = price - self.entry_price
        else:  # short
            price_change = self.entry_price - price

        self.unrealized_pnl = price_change * self.amount
        self.unrealized_pnl_percent = (price_change / self.entry_price) * 100 * self.leverage

    def get_roe(self) -> float:
        """Get return on equity (ROE) percentage."""
        if self.margin_used == 0:
            return 0.0
        return (self.unrealized_pnl / self.margin_used) * 100

    def should_liquidate(self, liquidation_margin_ratio: float = 0.9) -> bool:
        """
        Check if position is near liquidation.

        Args:
            liquidation_margin_ratio: Margin ratio threshold (0.9 = 90% of margin used)

        Returns:
            True if position is at risk of liquidation
        """
        # Calculate current margin ratio
        loss_amount = abs(min(0, self.unrealized_pnl))
        remaining_margin = self.margin_used - loss_amount

        if remaining_margin <= 0:
            return True

        margin_ratio = remaining_margin / self.margin_used

        return margin_ratio < liquidation_margin_ratio

    def to_dict(self) -> Dict:
        """Convert position to dictionary."""
        return {
            'symbol': self.symbol,
            'side': self.side,
            'entry_price': self.entry_price,
            'current_price': self.current_price,
            'amount': self.amount,
            'leverage': self.leverage,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'position_value': self.position_value,
            'margin_used': self.margin_used,
            'unrealized_pnl': self.unrealized_pnl,
            'unrealized_pnl_percent': self.unrealized_pnl_percent,
            'roe': self.get_roe(),
            'timestamp': self.timestamp,
        }


class MultiSymbolPortfolioManager:
    """
    Manages multiple futures positions across different symbols.
    """

    def __init__(self, initial_capital: float, max_positions: int = 5,
                 risk_per_trade: float = 0.04, default_leverage: int = 10):
        """
        Initialize portfolio manager.

        Args:
            initial_capital: Initial capital in USDT
            max_positions: Maximum number of concurrent positions
            risk_per_trade: Risk per trade as percentage (0.04 = 4%)
            default_leverage: Default leverage multiplier
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.max_positions = max_positions
        self.risk_per_trade = risk_per_trade
        self.default_leverage = default_leverage

        # Active positions
        self.positions: Dict[str, FuturesPosition] = {}

        # Trade history
        self.trade_history = []

        # Portfolio metrics
        self.total_margin_used = 0.0
        self.total_unrealized_pnl = 0.0

        logger.info(f"MultiSymbolPortfolioManager initialized: "
                   f"Capital=${initial_capital:,.2f}, Max Positions={max_positions}, "
                   f"Risk={risk_per_trade*100}%, Default Leverage={default_leverage}x")

    def can_open_position(self) -> Tuple[bool, str]:
        """
        Check if a new position can be opened.

        Returns:
            Tuple of (can_open, reason)
        """
        if len(self.positions) >= self.max_positions:
            return False, f"Maximum positions reached ({self.max_positions})"

        # Check available capital
        available_capital = self.current_capital - self.total_margin_used

        if available_capital < self.current_capital * self.risk_per_trade:
            return False, "Insufficient available capital"

        return True, ""

    def calculate_position_size(self, symbol: str, entry_price: float, stop_loss: float,
                                leverage: int, df: pd.DataFrame) -> float:
        """
        Calculate position size based on risk.

        Args:
            symbol: Trading pair
            entry_price: Entry price
            stop_loss: Stop loss price
            leverage: Leverage multiplier
            df: DataFrame with OHLCV data for ATR calculation

        Returns:
            Position size in base currency
        """
        # Calculate risk amount
        risk_amount = self.current_capital * self.risk_per_trade

        # Calculate risk per contract
        risk_per_contract = abs(entry_price - stop_loss)

        if risk_per_contract == 0:
            # Use ATR if stop loss is at entry
            atr = ATRCalculator.calculate_atr(
                df['high'].values,
                df['low'].values,
                df['close'].values,
                period=14
            )[-1]
            risk_per_contract = atr * 2

        # Calculate position size
        position_size = risk_amount / risk_per_contract

        # Apply leverage to reduce margin requirement
        # With leverage, we can control larger positions with less capital
        # But our risk calculation already accounts for the stop loss distance

        return position_size

    def open_position(self, symbol: str, side: str, entry_price: float,
                     stop_loss: float, take_profit: float, leverage: int,
                     df: pd.DataFrame) -> Optional[FuturesPosition]:
        """
        Open a new position.

        Args:
            symbol: Trading pair
            side: 'long' or 'short'
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            leverage: Leverage multiplier
            df: DataFrame with OHLCV data

        Returns:
            FuturesPosition object or None
        """
        # Check if can open
        can_open, reason = self.can_open_position()
        if not can_open:
            logger.warning(f"Cannot open position: {reason}")
            return None

        # Check if already have position in this symbol
        if symbol in self.positions:
            logger.warning(f"Already have open position in {symbol}")
            return None

        # Calculate position size
        amount = self.calculate_position_size(symbol, entry_price, stop_loss, leverage, df)

        # Create position
        position = FuturesPosition(
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            amount=amount,
            leverage=leverage,
            stop_loss=stop_loss,
            take_profit=take_profit,
            timestamp=datetime.now()
        )

        # Add to positions
        self.positions[symbol] = position

        # Update portfolio metrics
        self.total_margin_used += position.margin_used

        # Record trade
        trade_info = {
            'action': 'OPEN',
            'timestamp': position.timestamp,
            'symbol': symbol,
            'side': side,
            'entry_price': entry_price,
            'amount': amount,
            'leverage': leverage,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'margin_used': position.margin_used,
        }
        self.trade_history.append(trade_info)

        logger.info(f"Position opened: {symbol} {side} {amount:.4f} @ {entry_price:.2f} "
                   f"[{leverage}x leverage, Margin: ${position.margin_used:.2f}]")

        return position

    def close_position(self, symbol: str, exit_price: float, reason: str) -> Optional[Dict]:
        """
        Close a position.

        Args:
            symbol: Trading pair
            exit_price: Exit price
            reason: Reason for closing

        Returns:
            Trade information or None
        """
        if symbol not in self.positions:
            logger.warning(f"No position to close for {symbol}")
            return None

        position = self.positions[symbol]

        # Update price and calculate final P&L
        position.update_price(exit_price)

        # Calculate realized P&L
        realized_pnl = position.unrealized_pnl
        roe = position.get_roe()

        # Update capital
        self.current_capital += realized_pnl

        # Update portfolio metrics
        self.total_margin_used -= position.margin_used

        # Record trade
        trade_info = {
            'action': 'CLOSE',
            'timestamp': datetime.now(),
            'symbol': symbol,
            'side': position.side,
            'entry_price': position.entry_price,
            'exit_price': exit_price,
            'amount': position.amount,
            'leverage': position.leverage,
            'margin_used': position.margin_used,
            'realized_pnl': realized_pnl,
            'roe': roe,
            'reason': reason,
            'capital': self.current_capital,
        }
        self.trade_history.append(trade_info)

        # Remove position
        del self.positions[symbol]

        logger.info(f"Position closed: {symbol} @ {exit_price:.2f}, "
                   f"P&L: ${realized_pnl:.2f}, ROE: {roe:.2f}%, Reason: {reason}")

        return trade_info

    def update_all_positions(self, prices: Dict[str, float]):
        """
        Update all positions with current prices.

        Args:
            prices: Dictionary of {symbol: price}
        """
        self.total_unrealized_pnl = 0.0

        for symbol, position in self.positions.items():
            if symbol in prices:
                position.update_price(prices[symbol])
                self.total_unrealized_pnl += position.unrealized_pnl

    def check_exit_conditions(self, symbol: str, current_price: float) -> Tuple[bool, str]:
        """
        Check if position should be exited.

        Args:
            symbol: Trading pair
            current_price: Current price

        Returns:
            Tuple of (should_exit, reason)
        """
        if symbol not in self.positions:
            return False, ""

        position = self.positions[symbol]
        position.update_price(current_price)

        # Check stop loss
        if position.side == 'long':
            if current_price <= position.stop_loss:
                return True, "STOP_LOSS"
            if current_price >= position.take_profit:
                return True, "TAKE_PROFIT"
        else:  # short
            if current_price >= position.stop_loss:
                return True, "STOP_LOSS"
            if current_price <= position.take_profit:
                return True, "TAKE_PROFIT"

        # Check liquidation risk
        if position.should_liquidate():
            return True, "LIQUIDATION_RISK"

        return False, ""

    def get_available_capital(self) -> float:
        """Get available capital for new positions."""
        return self.current_capital - self.total_margin_used

    def get_portfolio_value(self) -> float:
        """Get total portfolio value including unrealized P&L."""
        return self.current_capital + self.total_unrealized_pnl

    def get_portfolio_stats(self) -> Dict:
        """Get portfolio statistics."""
        closed_trades = [t for t in self.trade_history if t['action'] == 'CLOSE']

        if not closed_trades:
            return {
                'total_trades': 0,
                'open_positions': len(self.positions),
            }

        pnls = [t['realized_pnl'] for t in closed_trades]
        winning_trades = [p for p in pnls if p > 0]
        losing_trades = [p for p in pnls if p < 0]

        stats = {
            'initial_capital': self.initial_capital,
            'current_capital': self.current_capital,
            'total_unrealized_pnl': self.total_unrealized_pnl,
            'portfolio_value': self.get_portfolio_value(),
            'margin_used': self.total_margin_used,
            'available_capital': self.get_available_capital(),
            'open_positions': len(self.positions),
            'max_positions': self.max_positions,
            'total_trades': len(closed_trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': len(winning_trades) / len(closed_trades) * 100 if closed_trades else 0,
            'total_pnl': sum(pnls),
            'avg_win': np.mean(winning_trades) if winning_trades else 0,
            'avg_loss': np.mean(losing_trades) if losing_trades else 0,
            'total_return': (self.current_capital / self.initial_capital - 1) * 100,
        }

        return stats

    def get_position_summary(self) -> List[Dict]:
        """Get summary of all open positions."""
        return [pos.to_dict() for pos in self.positions.values()]

    def get_total_exposure(self) -> float:
        """Get total exposure (position value) across all positions."""
        return sum(pos.position_value for pos in self.positions.values())

    def get_symbols_in_portfolio(self) -> List[str]:
        """Get list of symbols with open positions."""
        return list(self.positions.keys())
