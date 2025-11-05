"""
Risk management module for position sizing and risk control.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
import logging

from src.config import config

logger = logging.getLogger(__name__)


class RiskManager:
    """
    Risk management for trading bot.
    Handles position sizing, risk limits, and portfolio management.
    """

    def __init__(self, initial_capital: float, max_risk_per_trade: float = 0.02):
        """
        Initialize risk manager.

        Args:
            initial_capital: Initial portfolio capital
            max_risk_per_trade: Maximum risk per trade (as decimal, e.g., 0.02 for 2%)
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.max_risk_per_trade = max_risk_per_trade

        # Risk limits
        self.max_position_size = config.MAX_POSITION_SIZE  # Max % of portfolio per position
        self.max_drawdown_limit = 0.20  # Max 20% drawdown before stopping
        self.daily_loss_limit = 0.05  # Max 5% daily loss

        # Tracking
        self.peak_capital = initial_capital
        self.daily_start_capital = initial_capital
        self.total_trades = 0
        self.losing_streak = 0
        self.winning_streak = 0

        logger.info(f"RiskManager initialized with capital: ${initial_capital:,.2f}")

    def update_capital(self, new_capital: float):
        """
        Update current capital.

        Args:
            new_capital: New capital value
        """
        self.current_capital = new_capital

        # Update peak capital
        if new_capital > self.peak_capital:
            self.peak_capital = new_capital

    def get_current_drawdown(self) -> float:
        """
        Get current drawdown percentage.

        Returns:
            Drawdown as percentage
        """
        if self.peak_capital == 0:
            return 0.0

        drawdown = (self.peak_capital - self.current_capital) / self.peak_capital
        return drawdown

    def get_daily_return(self) -> float:
        """
        Get daily return percentage.

        Returns:
            Daily return as percentage
        """
        if self.daily_start_capital == 0:
            return 0.0

        daily_return = (self.current_capital - self.daily_start_capital) / self.daily_start_capital
        return daily_return

    def check_risk_limits(self) -> tuple[bool, str]:
        """
        Check if risk limits are breached.

        Returns:
            Tuple of (can_trade, reason)
        """
        # Check max drawdown
        current_drawdown = self.get_current_drawdown()
        if current_drawdown >= self.max_drawdown_limit:
            return False, f"Max drawdown limit reached: {current_drawdown*100:.2f}%"

        # Check daily loss limit
        daily_return = self.get_daily_return()
        if daily_return <= -self.daily_loss_limit:
            return False, f"Daily loss limit reached: {daily_return*100:.2f}%"

        # Check minimum capital
        if self.current_capital < self.initial_capital * 0.5:
            return False, "Capital below 50% of initial value"

        return True, ""

    def calculate_position_size(self, entry_price: float, stop_loss_price: float,
                               confidence: float = 1.0) -> float:
        """
        Calculate position size based on risk parameters.

        Args:
            entry_price: Entry price
            stop_loss_price: Stop loss price
            confidence: Signal confidence (0-1)

        Returns:
            Position size in base currency
        """
        # Calculate risk per unit
        risk_per_unit = abs(entry_price - stop_loss_price)

        if risk_per_unit == 0:
            logger.warning("Risk per unit is zero, using default position size")
            return (self.current_capital * self.max_position_size) / entry_price

        # Calculate position size based on risk
        risk_amount = self.current_capital * self.max_risk_per_trade

        # Adjust for confidence
        risk_amount *= confidence

        # Position size
        position_size = risk_amount / risk_per_unit

        # Apply maximum position size limit
        max_position_value = self.current_capital * self.max_position_size
        max_position_size = max_position_value / entry_price

        position_size = min(position_size, max_position_size)

        logger.info(f"Calculated position size: {position_size:.6f} "
                   f"(risk: ${risk_amount:.2f}, confidence: {confidence:.2f})")

        return position_size

    def calculate_kelly_criterion(self, win_rate: float, avg_win: float,
                                  avg_loss: float) -> float:
        """
        Calculate Kelly Criterion for position sizing.

        Args:
            win_rate: Historical win rate (0-1)
            avg_win: Average win amount
            avg_loss: Average loss amount (positive value)

        Returns:
            Kelly percentage (0-1)
        """
        if avg_loss == 0 or win_rate == 0:
            return 0.0

        win_loss_ratio = avg_win / avg_loss
        kelly = (win_rate * win_loss_ratio - (1 - win_rate)) / win_loss_ratio

        # Apply fractional Kelly (half Kelly for safety)
        kelly = max(0, min(kelly * 0.5, self.max_position_size))

        return kelly

    def should_reduce_position_size(self) -> tuple[bool, float]:
        """
        Determine if position size should be reduced based on recent performance.

        Returns:
            Tuple of (should_reduce, reduction_factor)
        """
        # Reduce position size after losing streak
        if self.losing_streak >= 3:
            reduction_factor = 0.5  # Reduce to 50%
            return True, reduction_factor

        # Reduce position size if in significant drawdown
        current_drawdown = self.get_current_drawdown()
        if current_drawdown > 0.10:  # More than 10% drawdown
            reduction_factor = 1 - current_drawdown  # Proportional reduction
            return True, reduction_factor

        return False, 1.0

    def record_trade(self, pnl: float, was_win: bool):
        """
        Record a trade result for tracking.

        Args:
            pnl: Profit/Loss amount
            was_win: Whether trade was winning
        """
        self.total_trades += 1

        if was_win:
            self.winning_streak += 1
            self.losing_streak = 0
        else:
            self.losing_streak += 1
            self.winning_streak = 0

        logger.info(f"Trade recorded: {'WIN' if was_win else 'LOSS'}, "
                   f"P&L: ${pnl:.2f}, Streak: {self.winning_streak if was_win else -self.losing_streak}")

    def reset_daily_tracking(self):
        """Reset daily tracking metrics."""
        self.daily_start_capital = self.current_capital
        logger.info("Daily tracking reset")

    def get_risk_metrics(self) -> Dict:
        """
        Get current risk metrics.

        Returns:
            Dictionary of risk metrics
        """
        return {
            'current_capital': self.current_capital,
            'peak_capital': self.peak_capital,
            'current_drawdown': self.get_current_drawdown() * 100,
            'daily_return': self.get_daily_return() * 100,
            'total_return': (self.current_capital / self.initial_capital - 1) * 100,
            'winning_streak': self.winning_streak,
            'losing_streak': self.losing_streak,
            'total_trades': self.total_trades,
        }

    def validate_trade(self, position_value: float, entry_price: float,
                      stop_loss_price: float) -> tuple[bool, str]:
        """
        Validate if a trade meets risk requirements.

        Args:
            position_value: Total position value
            entry_price: Entry price
            stop_loss_price: Stop loss price

        Returns:
            Tuple of (is_valid, reason)
        """
        # Check if we can trade
        can_trade, reason = self.check_risk_limits()
        if not can_trade:
            return False, reason

        # Check position size limit
        max_position_value = self.current_capital * self.max_position_size
        if position_value > max_position_value:
            return False, f"Position size exceeds limit: ${position_value:.2f} > ${max_position_value:.2f}"

        # Check stop loss distance
        stop_loss_distance = abs(entry_price - stop_loss_price) / entry_price

        if stop_loss_distance < 0.005:  # Less than 0.5%
            return False, "Stop loss too tight (< 0.5%)"

        if stop_loss_distance > 0.10:  # More than 10%
            return False, "Stop loss too wide (> 10%)"

        # Check risk amount
        risk_amount = position_value * stop_loss_distance
        max_risk = self.current_capital * self.max_risk_per_trade

        if risk_amount > max_risk:
            return False, f"Risk amount exceeds limit: ${risk_amount:.2f} > ${max_risk:.2f}"

        return True, "Trade validated"


class PortfolioManager:
    """
    Portfolio management for multiple positions.
    """

    def __init__(self, initial_capital: float):
        """
        Initialize portfolio manager.

        Args:
            initial_capital: Initial capital
        """
        self.initial_capital = initial_capital
        self.positions = {}
        self.cash = initial_capital

    def add_position(self, symbol: str, amount: float, entry_price: float):
        """Add a position to the portfolio."""
        if symbol in self.positions:
            # Average up/down
            current = self.positions[symbol]
            total_cost = (current['amount'] * current['avg_price']) + (amount * entry_price)
            total_amount = current['amount'] + amount
            avg_price = total_cost / total_amount

            self.positions[symbol] = {
                'amount': total_amount,
                'avg_price': avg_price,
            }
        else:
            self.positions[symbol] = {
                'amount': amount,
                'avg_price': entry_price,
            }

        self.cash -= amount * entry_price

    def remove_position(self, symbol: str, current_price: float) -> float:
        """
        Remove a position from the portfolio.

        Returns:
            Realized P&L
        """
        if symbol not in self.positions:
            return 0.0

        position = self.positions[symbol]
        proceeds = position['amount'] * current_price
        cost = position['amount'] * position['avg_price']
        pnl = proceeds - cost

        self.cash += proceeds
        del self.positions[symbol]

        return pnl

    def get_portfolio_value(self, prices: Dict[str, float]) -> float:
        """
        Get total portfolio value.

        Args:
            prices: Dictionary of current prices for each symbol

        Returns:
            Total portfolio value
        """
        position_value = sum(
            pos['amount'] * prices.get(symbol, pos['avg_price'])
            for symbol, pos in self.positions.items()
        )

        return self.cash + position_value

    def get_position_allocation(self, prices: Dict[str, float]) -> Dict[str, float]:
        """
        Get allocation percentage for each position.

        Args:
            prices: Dictionary of current prices

        Returns:
            Dictionary of allocation percentages
        """
        total_value = self.get_portfolio_value(prices)

        if total_value == 0:
            return {}

        allocations = {}
        for symbol, pos in self.positions.items():
            position_value = pos['amount'] * prices.get(symbol, pos['avg_price'])
            allocations[symbol] = (position_value / total_value) * 100

        return allocations
