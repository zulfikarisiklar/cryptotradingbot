"""
Emergency stop and safety systems for the trading bot.
Handles market crashes, circuit breakers, and high-volatility periods.
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
from datetime import datetime, time
import logging
import pytz

logger = logging.getLogger(__name__)


class EmergencyStop:
    """
    Emergency stop system for handling market crashes and extreme conditions.
    """

    def __init__(self):
        """Initialize emergency stop system."""
        self.emergency_active = False
        self.emergency_reason = ""
        self.emergency_timestamp = None

        # Thresholds
        self.crash_threshold_1m = -0.05  # -5% in 1 minute
        self.crash_threshold_5m = -0.10  # -10% in 5 minutes
        self.crash_threshold_15m = -0.15  # -15% in 15 minutes
        self.volume_spike_threshold = 5.0  # 5x normal volume

        logger.info("EmergencyStop system initialized")

    def check_price_crash(self, df: pd.DataFrame) -> Tuple[bool, str]:
        """
        Check for sudden price crashes.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Tuple of (is_crash, reason)
        """
        if len(df) < 20:
            return False, ""

        current_price = df['close'].iloc[-1]

        # Check 1-minute crash (last candle)
        if len(df) >= 2:
            prev_price_1m = df['close'].iloc[-2]
            change_1m = (current_price - prev_price_1m) / prev_price_1m

            if change_1m <= self.crash_threshold_1m:
                return True, f"1-minute crash detected: {change_1m*100:.2f}%"

        # Check 5-minute crash (last 5 candles)
        if len(df) >= 6:
            prev_price_5m = df['close'].iloc[-6]
            change_5m = (current_price - prev_price_5m) / prev_price_5m

            if change_5m <= self.crash_threshold_5m:
                return True, f"5-minute crash detected: {change_5m*100:.2f}%"

        # Check 15-minute crash (last 15 candles)
        if len(df) >= 16:
            prev_price_15m = df['close'].iloc[-16]
            change_15m = (current_price - prev_price_15m) / prev_price_15m

            if change_15m <= self.crash_threshold_15m:
                return True, f"15-minute crash detected: {change_15m*100:.2f}%"

        return False, ""

    def check_volume_spike(self, df: pd.DataFrame) -> Tuple[bool, str]:
        """
        Check for abnormal volume spikes.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Tuple of (is_spike, reason)
        """
        if len(df) < 20:
            return False, ""

        current_volume = df['volume'].iloc[-1]

        # Calculate average volume (20 periods)
        avg_volume = df['volume'].iloc[-21:-1].mean()

        if avg_volume == 0:
            return False, ""

        volume_ratio = current_volume / avg_volume

        if volume_ratio >= self.volume_spike_threshold:
            return True, f"Extreme volume spike: {volume_ratio:.1f}x average"

        return False, ""

    def check_volatility_explosion(self, df: pd.DataFrame) -> Tuple[bool, str]:
        """
        Check for extreme volatility.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Tuple of (is_extreme, reason)
        """
        if len(df) < 20:
            return False, ""

        # Calculate recent volatility
        recent_returns = df['close'].pct_change().iloc[-10:]
        recent_volatility = recent_returns.std()

        # Calculate historical volatility
        historical_returns = df['close'].pct_change().iloc[-100:-10]
        historical_volatility = historical_returns.std()

        if historical_volatility == 0:
            return False, ""

        volatility_ratio = recent_volatility / historical_volatility

        # If recent volatility is 3x historical, it's extreme
        if volatility_ratio >= 3.0:
            return True, f"Volatility explosion: {volatility_ratio:.1f}x normal"

        return False, ""

    def trigger_emergency_stop(self, reason: str):
        """
        Trigger emergency stop.

        Args:
            reason: Reason for emergency stop
        """
        self.emergency_active = True
        self.emergency_reason = reason
        self.emergency_timestamp = datetime.now()

        logger.critical(f"🚨 EMERGENCY STOP TRIGGERED: {reason}")

    def reset_emergency_stop(self):
        """Reset emergency stop after manual review."""
        logger.warning("Resetting emergency stop - ensure market has stabilized!")
        self.emergency_active = False
        self.emergency_reason = ""
        self.emergency_timestamp = None

    def check_all_conditions(self, df: pd.DataFrame) -> Tuple[bool, str]:
        """
        Check all emergency conditions.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Tuple of (should_stop, reason)
        """
        # Check price crash
        is_crash, crash_reason = self.check_price_crash(df)
        if is_crash:
            return True, crash_reason

        # Check volume spike
        is_spike, spike_reason = self.check_volume_spike(df)
        if is_spike:
            return True, spike_reason

        # Check volatility explosion
        is_extreme, volatility_reason = self.check_volatility_explosion(df)
        if is_extreme:
            return True, volatility_reason

        return False, ""


class MarketHoursFilter:
    """
    Filter trading based on stock market opening hours.
    Avoids high-volatility periods during major market openings.
    """

    def __init__(self):
        """Initialize market hours filter."""
        # Define market opening times (UTC)
        self.asian_markets = {
            'Tokyo': (time(0, 0), time(1, 0)),      # 09:00-10:00 JST (00:00-01:00 UTC)
            'Hong Kong': (time(1, 30), time(2, 30)),  # 09:30-10:30 HKT (01:30-02:30 UTC)
            'Shanghai': (time(1, 30), time(2, 30)),   # 09:30-10:30 CST (01:30-02:30 UTC)
        }

        self.us_markets = {
            'NYSE/NASDAQ': (time(14, 30), time(15, 30)),  # 09:30-10:30 EST (14:30-15:30 UTC)
        }

        # Blackout period: 30 min before and after opening
        self.blackout_buffer_minutes = 30

        logger.info("MarketHoursFilter initialized")

    def is_asian_market_opening(self, dt: Optional[datetime] = None) -> Tuple[bool, str]:
        """
        Check if it's Asian market opening time.

        Args:
            dt: Datetime to check (uses current UTC time if None)

        Returns:
            Tuple of (is_opening, market_name)
        """
        if dt is None:
            dt = datetime.now(pytz.UTC)
        elif dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)

        current_time = dt.time()

        for market_name, (start_time, end_time) in self.asian_markets.items():
            if start_time <= current_time <= end_time:
                return True, market_name

        return False, ""

    def is_us_market_opening(self, dt: Optional[datetime] = None) -> Tuple[bool, str]:
        """
        Check if it's US market opening time.

        Args:
            dt: Datetime to check (uses current UTC time if None)

        Returns:
            Tuple of (is_opening, market_name)
        """
        if dt is None:
            dt = datetime.now(pytz.UTC)
        elif dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)

        current_time = dt.time()

        for market_name, (start_time, end_time) in self.us_markets.items():
            if start_time <= current_time <= end_time:
                return True, market_name

        return False, ""

    def should_avoid_trading(self, dt: Optional[datetime] = None) -> Tuple[bool, str]:
        """
        Check if trading should be avoided due to market openings.

        Args:
            dt: Datetime to check (uses current UTC time if None)

        Returns:
            Tuple of (should_avoid, reason)
        """
        # Check Asian market openings
        is_asian_opening, asian_market = self.is_asian_market_opening(dt)
        if is_asian_opening:
            return True, f"Asian market opening: {asian_market}"

        # Check US market openings
        is_us_opening, us_market = self.is_us_market_opening(dt)
        if is_us_opening:
            return True, f"US market opening: {us_market}"

        return False, ""

    def is_weekend(self, dt: Optional[datetime] = None) -> bool:
        """
        Check if it's weekend (crypto markets are 24/7 but stock markets are closed).

        Args:
            dt: Datetime to check

        Returns:
            True if weekend
        """
        if dt is None:
            dt = datetime.now(pytz.UTC)

        # Saturday=5, Sunday=6
        return dt.weekday() >= 5


class CircuitBreaker:
    """
    Circuit breaker to halt trading during extreme conditions.
    """

    def __init__(self):
        """Initialize circuit breaker."""
        self.tripped = False
        self.trip_count = 0
        self.last_trip_time = None
        self.cooldown_minutes = 60  # 1 hour cooldown after trip

        # Thresholds
        self.drawdown_threshold = 0.15  # 15% drawdown triggers breaker
        self.consecutive_losses_threshold = 5
        self.rapid_loss_threshold = 0.10  # 10% loss in short time

        logger.info("CircuitBreaker initialized")

    def check_drawdown_trigger(self, peak_capital: float, current_capital: float) -> bool:
        """
        Check if drawdown exceeds threshold.

        Args:
            peak_capital: Peak capital value
            current_capital: Current capital value

        Returns:
            True if circuit breaker should trip
        """
        if peak_capital == 0:
            return False

        drawdown = (peak_capital - current_capital) / peak_capital

        if drawdown >= self.drawdown_threshold:
            logger.critical(f"Circuit breaker: Drawdown {drawdown*100:.2f}% exceeds threshold")
            return True

        return False

    def check_consecutive_losses(self, recent_trades: list) -> bool:
        """
        Check for consecutive losing trades.

        Args:
            recent_trades: List of recent trade results

        Returns:
            True if circuit breaker should trip
        """
        if len(recent_trades) < self.consecutive_losses_threshold:
            return False

        # Check last N trades
        last_trades = recent_trades[-self.consecutive_losses_threshold:]
        all_losses = all(trade.get('pnl', 0) < 0 for trade in last_trades)

        if all_losses:
            logger.critical(f"Circuit breaker: {self.consecutive_losses_threshold} consecutive losses")
            return True

        return False

    def trip_breaker(self, reason: str):
        """
        Trip the circuit breaker.

        Args:
            reason: Reason for tripping
        """
        self.tripped = True
        self.trip_count += 1
        self.last_trip_time = datetime.now()

        logger.critical(f"⚡ CIRCUIT BREAKER TRIPPED: {reason}")
        logger.critical(f"Trip count: {self.trip_count}")

    def can_reset(self) -> Tuple[bool, str]:
        """
        Check if circuit breaker can be reset.

        Returns:
            Tuple of (can_reset, reason)
        """
        if not self.tripped:
            return True, "Circuit breaker not tripped"

        if self.last_trip_time is None:
            return True, "No previous trip"

        time_since_trip = (datetime.now() - self.last_trip_time).total_seconds() / 60

        if time_since_trip < self.cooldown_minutes:
            remaining = self.cooldown_minutes - time_since_trip
            return False, f"Cooldown period: {remaining:.0f} minutes remaining"

        return True, "Cooldown period complete"

    def reset_breaker(self):
        """Reset circuit breaker after cooldown."""
        can_reset, reason = self.can_reset()

        if not can_reset:
            logger.warning(f"Cannot reset circuit breaker: {reason}")
            return False

        logger.warning("Resetting circuit breaker")
        self.tripped = False
        return True


class SafetyManager:
    """
    Comprehensive safety manager combining all safety systems.
    """

    def __init__(self):
        """Initialize safety manager."""
        self.emergency_stop = EmergencyStop()
        self.market_hours = MarketHoursFilter()
        self.circuit_breaker = CircuitBreaker()

        self.trading_halted = False
        self.halt_reason = ""

        logger.info("SafetyManager initialized with all safety systems")

    def check_safety_conditions(self, df: pd.DataFrame,
                                peak_capital: float,
                                current_capital: float,
                                recent_trades: list) -> Tuple[bool, str]:
        """
        Check all safety conditions before allowing trading.

        Args:
            df: Market data
            peak_capital: Peak capital value
            current_capital: Current capital value
            recent_trades: Recent trade history

        Returns:
            Tuple of (is_safe, reason)
        """
        # Check if emergency stop is already active
        if self.emergency_stop.emergency_active:
            return False, f"Emergency stop active: {self.emergency_stop.emergency_reason}"

        # Check if circuit breaker is tripped
        if self.circuit_breaker.tripped:
            return False, "Circuit breaker tripped"

        # Check emergency conditions (crashes, volume spikes)
        should_stop, stop_reason = self.emergency_stop.check_all_conditions(df)
        if should_stop:
            self.emergency_stop.trigger_emergency_stop(stop_reason)
            self.close_all_positions_signal()
            return False, stop_reason

        # Check market hours (avoid stock market openings)
        should_avoid, avoid_reason = self.market_hours.should_avoid_trading()
        if should_avoid:
            logger.warning(f"Trading paused: {avoid_reason}")
            return False, avoid_reason

        # Check circuit breaker conditions
        if self.circuit_breaker.check_drawdown_trigger(peak_capital, current_capital):
            self.circuit_breaker.trip_breaker("Excessive drawdown")
            self.close_all_positions_signal()
            return False, "Circuit breaker: Excessive drawdown"

        if self.circuit_breaker.check_consecutive_losses(recent_trades):
            self.circuit_breaker.trip_breaker("Consecutive losses")
            self.close_all_positions_signal()
            return False, "Circuit breaker: Consecutive losses"

        return True, "All safety checks passed"

    def close_all_positions_signal(self):
        """Signal to close all positions immediately."""
        logger.critical("🚨 CLOSE ALL POSITIONS - EMERGENCY/CIRCUIT BREAKER TRIGGERED")
        self.trading_halted = True
        self.halt_reason = "Safety system triggered"

    def should_close_positions(self) -> bool:
        """Check if positions should be closed."""
        return (self.emergency_stop.emergency_active or
                self.circuit_breaker.tripped or
                self.trading_halted)

    def get_status(self) -> Dict:
        """Get status of all safety systems."""
        return {
            'emergency_stop_active': self.emergency_stop.emergency_active,
            'emergency_reason': self.emergency_stop.emergency_reason,
            'circuit_breaker_tripped': self.circuit_breaker.tripped,
            'circuit_breaker_trips': self.circuit_breaker.trip_count,
            'trading_halted': self.trading_halted,
            'halt_reason': self.halt_reason,
            'can_reset_breaker': self.circuit_breaker.can_reset()[0],
        }

    def reset_all_systems(self):
        """Reset all safety systems (requires manual intervention)."""
        logger.warning("⚠️  RESETTING ALL SAFETY SYSTEMS - ENSURE MARKET IS STABLE!")

        # Reset emergency stop
        self.emergency_stop.reset_emergency_stop()

        # Reset circuit breaker
        self.circuit_breaker.reset_breaker()

        # Reset trading halt
        self.trading_halted = False
        self.halt_reason = ""

        logger.info("All safety systems reset")
