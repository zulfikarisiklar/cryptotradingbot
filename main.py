"""
Main trading bot orchestrator.
Combines all components for live trading.
"""

import time
from datetime import datetime, timedelta
import logging
import argparse
import sys

from src.config import config
from src.exchange.binance_client import BinanceClient
from src.data.data_manager import DataManager
from src.strategy.trading_strategy import TradingStrategy
from src.ml.ml_engine import MLEngine
from src.sentiment.sentiment_analyzer import SentimentAnalyzer
from src.risk.risk_manager import RiskManager
from src.utils.logger import setup_logger

logger = setup_logger('trading_bot')


class TradingBot:
    """
    Main trading bot orchestrator.
    Combines all components for automated trading.
    """

    def __init__(self, symbol: str, timeframe: str, initial_capital: float,
                 mode: str = 'paper'):
        """
        Initialize trading bot.

        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            timeframe: Timeframe (e.g., '1h')
            initial_capital: Initial capital
            mode: 'paper' or 'live'
        """
        self.symbol = symbol
        self.timeframe = timeframe
        self.initial_capital = initial_capital
        self.mode = mode

        logger.info(f"Initializing Trading Bot - {symbol} {timeframe} ({mode} mode)")

        # Initialize components
        self.client = BinanceClient()
        self.data_manager = DataManager()
        self.strategy = TradingStrategy(symbol, initial_capital)
        self.ml_engine = MLEngine()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.risk_manager = RiskManager(initial_capital)

        # Bot state
        self.is_running = False
        self.last_retrain_time = None

        logger.info("Trading Bot initialized successfully")

    def initialize(self):
        """Initialize bot with historical data and train ML models."""
        logger.info("Initializing bot with historical data...")

        # Fetch historical data
        logger.info("Fetching historical data...")
        self.data_manager.fetch_historical_bulk(
            self.client,
            self.symbol,
            self.timeframe,
            days_back=365
        )

        # Load data
        df = self.data_manager.load_ohlcv(self.symbol, self.timeframe, limit=1000)

        if df.empty:
            logger.error("Failed to load historical data")
            sys.exit(1)

        logger.info(f"Loaded {len(df)} candles")

        # Train ML models
        logger.info("Training ML models...")
        training_scores = self.ml_engine.train(df, symbol=self.symbol)

        logger.info("Training complete:")
        for model_name, scores in training_scores.items():
            logger.info(f"  {model_name}: Accuracy={scores['accuracy']:.3f}, "
                       f"F1={scores['f1']:.3f}")

        self.last_retrain_time = datetime.now()

        logger.info("Initialization complete")

    def update_data(self):
        """Update latest market data."""
        try:
            self.data_manager.update_latest_data(
                self.client,
                self.symbol,
                self.timeframe,
                limit=100
            )
        except Exception as e:
            logger.error(f"Error updating data: {e}")

    def get_current_data(self) -> 'pd.DataFrame':
        """Get current market data."""
        df = self.data_manager.load_ohlcv(
            self.symbol,
            self.timeframe,
            limit=500
        )
        return df

    def check_and_retrain(self):
        """Check if ML models need retraining."""
        if self.last_retrain_time is None:
            return

        hours_since_retrain = (datetime.now() - self.last_retrain_time).total_seconds() / 3600

        if hours_since_retrain >= config.ML_RETRAIN_INTERVAL:
            logger.info("Retraining ML models...")

            df = self.get_current_data()
            self.ml_engine.train(df, symbol=self.symbol)

            self.last_retrain_time = datetime.now()
            logger.info("Retraining complete")

    def execute_trade(self, action: str, amount: float):
        """
        Execute a trade on the exchange.

        Args:
            action: 'buy' or 'sell'
            amount: Amount to trade
        """
        if self.mode == 'paper':
            logger.info(f"[PAPER] {action.upper()} {amount:.6f} {self.symbol}")
            return

        # Live trading
        try:
            if action == 'buy':
                order = self.client.create_market_order(self.symbol, 'buy', amount)
                logger.info(f"Buy order executed: {order}")
            elif action == 'sell':
                order = self.client.create_market_order(self.symbol, 'sell', amount)
                logger.info(f"Sell order executed: {order}")
        except Exception as e:
            logger.error(f"Error executing trade: {e}")

    def run_trading_cycle(self):
        """Run one trading cycle."""
        try:
            # Update data
            self.update_data()

            # Get current data
            df = self.get_current_data()

            if df.empty or len(df) < 200:
                logger.warning("Insufficient data for trading")
                return

            current_timestamp = df.index[-1]
            current_price = df.iloc[-1]['close']

            logger.info(f"Trading cycle at {current_timestamp}, Price: {current_price:.2f}")

            # Check risk limits
            can_trade, reason = self.risk_manager.check_risk_limits()
            if not can_trade:
                logger.warning(f"Trading halted: {reason}")
                return

            # Get ML prediction
            ml_prediction, ml_confidence = self.ml_engine.predict(
                df,
                symbol=self.symbol,
                ensemble=True
            )

            logger.info(f"ML Prediction: {ml_prediction} (confidence: {ml_confidence:.3f})")

            # Get sentiment signal
            sentiment_signal = 0.0
            if config.ENABLE_SENTIMENT:
                try:
                    sentiment_signal, sentiment_direction = self.sentiment_analyzer.get_sentiment_signal(
                        self.symbol
                    )
                    logger.info(f"Sentiment: {sentiment_direction} ({sentiment_signal:.3f})")
                except Exception as e:
                    logger.warning(f"Error getting sentiment: {e}")

            # Update risk manager
            self.risk_manager.update_capital(self.strategy.capital)

            # Trading logic
            if self.strategy.position:
                # Check exit conditions
                should_exit, exit_reason = self.strategy.check_exit_signal(df)

                if should_exit:
                    trade_info = self.strategy.close_position(df, current_timestamp, exit_reason)

                    # Execute sell order
                    if trade_info:
                        self.execute_trade('sell', trade_info['amount'])

                        # Record trade in risk manager
                        was_win = trade_info['pnl'] > 0
                        self.risk_manager.record_trade(trade_info['pnl'], was_win)

                        logger.info(f"Position closed: P&L ${trade_info['pnl']:.2f} "
                                   f"({trade_info['pnl_percent']:.2f}%)")

                # Check pyramid conditions
                elif self.strategy.check_pyramid_entry(df, ml_confidence):
                    trade_info = self.strategy.add_pyramid_level(df, current_timestamp)

                    if trade_info:
                        self.execute_trade('buy', trade_info['amount'])
                        logger.info(f"Pyramid level added")

            else:
                # Check entry conditions
                if self.strategy.check_entry_signal(
                    df,
                    ml_prediction,
                    ml_confidence,
                    sentiment_signal
                ):
                    trade_info = self.strategy.open_position(df, current_timestamp)

                    if trade_info:
                        # Validate with risk manager
                        is_valid, validation_msg = self.risk_manager.validate_trade(
                            trade_info['position_value'],
                            trade_info['price'],
                            trade_info['stop_loss']
                        )

                        if is_valid:
                            self.execute_trade('buy', trade_info['amount'])
                            logger.info(f"Position opened")
                        else:
                            logger.warning(f"Trade rejected: {validation_msg}")
                            # Cancel the position
                            self.strategy.position = None

            # Log current status
            risk_metrics = self.risk_manager.get_risk_metrics()
            logger.info(f"Capital: ${risk_metrics['current_capital']:,.2f}, "
                       f"Return: {risk_metrics['total_return']:.2f}%, "
                       f"Drawdown: {risk_metrics['current_drawdown']:.2f}%")

        except Exception as e:
            logger.error(f"Error in trading cycle: {e}", exc_info=True)

    def run(self, check_interval: int = 300):
        """
        Run the trading bot.

        Args:
            check_interval: Interval between checks in seconds (default 5 minutes)
        """
        logger.info(f"Starting trading bot (check interval: {check_interval}s)")

        self.is_running = True

        try:
            while self.is_running:
                # Run trading cycle
                self.run_trading_cycle()

                # Check if models need retraining
                self.check_and_retrain()

                # Wait for next cycle
                logger.info(f"Waiting {check_interval}s until next cycle...")
                time.sleep(check_interval)

        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
        finally:
            self.stop()

    def stop(self):
        """Stop the trading bot."""
        logger.info("Stopping trading bot...")

        self.is_running = False

        # Close any open positions (optional)
        # if self.strategy.position:
        #     logger.info("Closing open position...")
        #     df = self.get_current_data()
        #     self.strategy.close_position(df, datetime.now(), "BOT_STOPPED")

        # Print final statistics
        stats = self.strategy.get_performance_stats()
        logger.info("Final Statistics:")
        logger.info(f"  Total Trades: {stats.get('total_trades', 0)}")
        logger.info(f"  Win Rate: {stats.get('win_rate', 0):.2f}%")
        logger.info(f"  Final Capital: ${self.strategy.capital:,.2f}")
        logger.info(f"  Total Return: {stats.get('total_return', 0):.2f}%")

        logger.info("Trading bot stopped")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Crypto Trading Bot')

    parser.add_argument('--symbol', type=str, default=config.TRADING_SYMBOL,
                       help='Trading pair (e.g., BTC/USDT)')
    parser.add_argument('--timeframe', type=str, default=config.TRADING_TIMEFRAME,
                       help='Timeframe (e.g., 1h)')
    parser.add_argument('--capital', type=float, default=config.INITIAL_CAPITAL,
                       help='Initial capital')
    parser.add_argument('--mode', type=str, default='paper', choices=['paper', 'live'],
                       help='Trading mode')
    parser.add_argument('--interval', type=int, default=300,
                       help='Check interval in seconds')

    args = parser.parse_args()

    # Validate configuration
    try:
        config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    # Create and run bot
    bot = TradingBot(
        symbol=args.symbol,
        timeframe=args.timeframe,
        initial_capital=args.capital,
        mode=args.mode
    )

    # Initialize bot
    bot.initialize()

    # Run bot
    bot.run(check_interval=args.interval)


if __name__ == '__main__':
    main()
