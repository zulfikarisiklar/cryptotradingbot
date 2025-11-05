"""
Futures trading bot with multi-symbol portfolio management.
Dynamically finds and trades the best opportunities with leverage.

⚠️ DISCLAIMER: THIS IS NOT INVESTMENT ADVICE ⚠️
This software is for educational purposes only.
Futures trading is EXTREMELY HIGH RISK.
USE AT YOUR OWN RISK. Not financial advice.
"""

import time
from datetime import datetime
import logging
import argparse
import sys

from src.config import config
from src.exchange.futures_client import BinanceFuturesClient
from src.data.data_manager import DataManager
from src.strategy.multi_symbol_portfolio import MultiSymbolPortfolioManager
from src.strategy.signal_scanner import SignalScanner
from src.ml.ml_engine import MLEngine
from src.sentiment.sentiment_analyzer import SentimentAnalyzer
from src.utils.safety import SafetyManager
from src.utils.logger import setup_logger

logger = setup_logger('futures_bot')


class FuturesTradingBot:
    """
    Multi-symbol futures trading bot with leverage.
    Automatically finds and trades the best opportunities.
    """

    def __init__(self, initial_capital: float, max_positions: int = 5,
                 risk_per_trade: float = 0.04, default_leverage: int = 10,
                 timeframe: str = '1h', mode: str = 'paper'):
        """
        Initialize futures trading bot.

        Args:
            initial_capital: Initial capital in USDT
            max_positions: Maximum concurrent positions
            risk_per_trade: Risk per trade (0.04 = 4%)
            default_leverage: Default leverage multiplier
            timeframe: Trading timeframe
            mode: 'paper' or 'live'
        """
        self.initial_capital = initial_capital
        self.max_positions = max_positions
        self.risk_per_trade = risk_per_trade
        self.default_leverage = default_leverage
        self.timeframe = timeframe
        self.mode = mode

        logger.info(f"Initializing Futures Trading Bot ({mode} mode)")
        logger.info(f"Capital: ${initial_capital:,.2f}, Max Positions: {max_positions}, "
                   f"Risk: {risk_per_trade*100}%, Leverage: {default_leverage}x")

        # Initialize components
        self.client = BinanceFuturesClient()
        self.data_manager = DataManager()
        self.portfolio = MultiSymbolPortfolioManager(
            initial_capital=initial_capital,
            max_positions=max_positions,
            risk_per_trade=risk_per_trade,
            default_leverage=default_leverage
        )
        self.ml_engine = MLEngine()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.signal_scanner = SignalScanner(
            client=self.client,
            ml_engine=self.ml_engine,
            sentiment_analyzer=self.sentiment_analyzer,
            timeframe=timeframe
        )
        self.safety_manager = SafetyManager()

        # Bot state
        self.is_running = False
        self.last_scan_time = None

        # User-configurable settings
        self.leverage = default_leverage
        self.atr_multiplier_sl = 2.0
        self.atr_multiplier_tp = 3.0

        logger.info("Futures Trading Bot initialized successfully")

    def set_user_settings(self, leverage: int = None, stop_loss_atr: float = None,
                         take_profit_atr: float = None):
        """
        Set user-configurable trading parameters.

        Args:
            leverage: Leverage multiplier (1-125)
            stop_loss_atr: Stop loss ATR multiplier
            take_profit_atr: Take profit ATR multiplier
        """
        if leverage:
            self.leverage = max(1, min(125, leverage))
            logger.info(f"Leverage set to {self.leverage}x")

        if stop_loss_atr:
            self.atr_multiplier_sl = stop_loss_atr
            logger.info(f"Stop loss ATR multiplier set to {stop_loss_atr}")

        if take_profit_atr:
            self.atr_multiplier_tp = take_profit_atr
            logger.info(f"Take profit ATR multiplier set to {take_profit_atr}")

    def initialize(self):
        """Initialize bot - train ML models if needed."""
        logger.info("Initializing bot...")

        # Try to load existing models
        try:
            self.ml_engine.load_all_models()
            logger.info("Loaded existing ML models")
        except:
            logger.info("No existing models found, will train on first data")

        logger.info("Initialization complete")

    def execute_futures_order(self, symbol: str, side: str, amount: float,
                              leverage: int, stop_loss: float, take_profit: float) -> bool:
        """
        Execute a futures order with stop loss and take profit.

        Args:
            symbol: Trading pair
            side: 'long' or 'short'
            amount: Position size
            leverage: Leverage multiplier
            stop_loss: Stop loss price
            take_profit: Take profit price

        Returns:
            True if successful
        """
        if self.mode == 'paper':
            logger.info(f"[PAPER] {side.upper()} {amount:.4f} {symbol} [{leverage}x] "
                       f"SL: {stop_loss:.2f}, TP: {take_profit:.2f}")
            return True

        try:
            # Set leverage and margin mode
            self.client.set_leverage(symbol, leverage)
            self.client.set_margin_mode(symbol, 'isolated')

            # Execute entry order
            order_side = 'buy' if side == 'long' else 'sell'
            entry_order = self.client.create_market_order(symbol, order_side, amount)

            logger.info(f"Entry order executed: {entry_order}")

            # Place stop loss order
            sl_side = 'sell' if side == 'long' else 'buy'
            sl_order = self.client.create_stop_market_order(
                symbol, sl_side, amount, stop_loss, reduce_only=True
            )

            logger.info(f"Stop loss order placed: {sl_order}")

            # Place take profit order
            tp_side = 'sell' if side == 'long' else 'buy'
            tp_order = self.client.create_take_profit_market_order(
                symbol, tp_side, amount, take_profit, reduce_only=True
            )

            logger.info(f"Take profit order placed: {tp_order}")

            return True

        except Exception as e:
            logger.error(f"Error executing futures order: {e}")
            return False

    def close_futures_position(self, symbol: str) -> bool:
        """
        Close a futures position.

        Args:
            symbol: Trading pair

        Returns:
            True if successful
        """
        if self.mode == 'paper':
            logger.info(f"[PAPER] CLOSE position for {symbol}")
            return True

        try:
            # Cancel all orders first
            self.client.cancel_all_orders(symbol)

            # Close position
            result = self.client.close_position(symbol)

            logger.info(f"Position closed: {result}")
            return True

        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return False

    def manage_positions(self):
        """Check and manage existing positions."""
        if not self.portfolio.positions:
            return

        # Get current prices for all positions
        prices = {}
        for symbol in self.portfolio.get_symbols_in_portfolio():
            try:
                ticker = self.client.fetch_ticker(symbol)
                prices[symbol] = ticker['last']
            except Exception as e:
                logger.error(f"Error fetching price for {symbol}: {e}")

        # Update all positions
        self.portfolio.update_all_positions(prices)

        # Check exit conditions for each position
        for symbol in list(self.portfolio.positions.keys()):
            current_price = prices.get(symbol)
            if not current_price:
                continue

            # Get position data
            df = self.client.fetch_ohlcv(symbol, self.timeframe, limit=200)

            # Check safety conditions
            is_safe, safety_reason = self.safety_manager.check_safety_conditions(
                df,
                self.portfolio.current_capital,
                self.portfolio.current_capital,
                self.portfolio.trade_history
            )

            # Emergency close if needed
            if self.safety_manager.should_close_positions():
                logger.critical(f"🚨 EMERGENCY: Closing {symbol} immediately!")
                if self.close_futures_position(symbol):
                    self.portfolio.close_position(symbol, current_price, "EMERGENCY_STOP")
                continue

            # Check normal exit conditions
            should_exit, reason = self.portfolio.check_exit_conditions(symbol, current_price)

            if should_exit:
                logger.info(f"Exit signal for {symbol}: {reason}")
                if self.close_futures_position(symbol):
                    self.portfolio.close_position(symbol, current_price, reason)

    def find_and_open_position(self):
        """Scan for new opportunities and open position if found."""
        # Check if we can open more positions
        can_open, reason = self.portfolio.can_open_position()
        if not can_open:
            logger.info(f"Cannot open new position: {reason}")
            return

        # Get symbols we already have positions in
        exclude_symbols = self.portfolio.get_symbols_in_portfolio()

        # Find best signal
        logger.info("Scanning market for opportunities...")
        signal = self.signal_scanner.get_best_signal(exclude_symbols=exclude_symbols)

        if not signal:
            logger.info("No strong signals found")
            return

        logger.info(f"Found signal: {signal.symbol} {signal.direction} "
                   f"(strength: {signal.strength:.1f})")
        logger.info(f"Reasons: {', '.join(signal.reasons)}")

        # Get data for position sizing
        df = self.client.fetch_ohlcv(signal.symbol, self.timeframe, limit=200)

        # Open position in portfolio
        position = self.portfolio.open_position(
            symbol=signal.symbol,
            side=signal.direction,
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            leverage=self.leverage,
            df=df
        )

        if position:
            # Execute on exchange
            success = self.execute_futures_order(
                symbol=signal.symbol,
                side=signal.direction,
                amount=position.amount,
                leverage=self.leverage,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit
            )

            if not success:
                # Rollback if execution failed
                self.portfolio.close_position(signal.symbol, signal.entry_price, "EXECUTION_FAILED")

    def run_trading_cycle(self):
        """Run one trading cycle."""
        try:
            logger.info("=" * 60)
            logger.info(f"Trading cycle at {datetime.now()}")

            # Manage existing positions first
            self.manage_positions()

            # Print portfolio status
            stats = self.portfolio.get_portfolio_stats()
            logger.info(f"Portfolio: ${stats['portfolio_value']:,.2f} "
                       f"({stats['total_return']:.2f}% return), "
                       f"Positions: {stats['open_positions']}/{self.max_positions}, "
                       f"Unrealized P&L: ${stats['total_unrealized_pnl']:.2f}")

            # Find and open new positions
            if stats['open_positions'] < self.max_positions:
                self.find_and_open_position()

            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Error in trading cycle: {e}", exc_info=True)

    def run(self, scan_interval: int = 300):
        """
        Run the futures trading bot.

        Args:
            scan_interval: Seconds between trading cycles
        """
        logger.info(f"Starting futures trading bot (scan interval: {scan_interval}s)")

        self.is_running = True

        try:
            while self.is_running:
                self.run_trading_cycle()

                # Wait for next cycle
                logger.info(f"Waiting {scan_interval}s until next cycle...\n")
                time.sleep(scan_interval)

        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
        finally:
            self.stop()

    def stop(self):
        """Stop the trading bot."""
        logger.info("Stopping futures trading bot...")

        self.is_running = False

        # Print final statistics
        stats = self.portfolio.get_portfolio_stats()
        logger.info("=" * 60)
        logger.info("FINAL STATISTICS")
        logger.info("=" * 60)
        logger.info(f"Initial Capital: ${stats.get('initial_capital', 0):,.2f}")
        logger.info(f"Final Capital: ${stats.get('current_capital', 0):,.2f}")
        logger.info(f"Total Return: {stats.get('total_return', 0):.2f}%")
        logger.info(f"Total Trades: {stats.get('total_trades', 0)}")
        logger.info(f"Win Rate: {stats.get('win_rate', 0):.2f}%")
        logger.info(f"Open Positions: {stats.get('open_positions', 0)}")
        logger.info("=" * 60)

        logger.info("Futures trading bot stopped")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Futures Trading Bot')

    parser.add_argument('--capital', type=float, default=10000,
                       help='Initial capital in USDT')
    parser.add_argument('--max-positions', type=int, default=5,
                       help='Maximum concurrent positions')
    parser.add_argument('--risk', type=float, default=0.04,
                       help='Risk per trade (0.04 = 4%%)')
    parser.add_argument('--leverage', type=int, default=10,
                       help='Default leverage (1-125)')
    parser.add_argument('--timeframe', type=str, default='1h',
                       help='Trading timeframe')
    parser.add_argument('--mode', type=str, default='paper', choices=['paper', 'live'],
                       help='Trading mode')
    parser.add_argument('--interval', type=int, default=300,
                       help='Scan interval in seconds')
    parser.add_argument('--stop-loss-atr', type=float, default=2.0,
                       help='Stop loss ATR multiplier')
    parser.add_argument('--take-profit-atr', type=float, default=3.0,
                       help='Take profit ATR multiplier')

    args = parser.parse_args()

    # Validate configuration
    try:
        config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    # Create bot
    bot = FuturesTradingBot(
        initial_capital=args.capital,
        max_positions=args.max_positions,
        risk_per_trade=args.risk,
        default_leverage=args.leverage,
        timeframe=args.timeframe,
        mode=args.mode
    )

    # Set user settings
    bot.set_user_settings(
        leverage=args.leverage,
        stop_loss_atr=args.stop_loss_atr,
        take_profit_atr=args.take_profit_atr
    )

    # Initialize bot
    bot.initialize()

    # Run bot
    bot.run(scan_interval=args.interval)


if __name__ == '__main__':
    main()
